def build_sunbed_power_analysis(sessions: list[Sun2TanningSession], samples: list[Any], bed_lookup: Dict[str, Any], ventilation_samples: Optional[list[Any]]=None) -> Dict[str, Any]:
    ROOF_EXHAUST_UNMETERED_W = dependencies.ROOF_EXHAUST_UNMETERED_W
    SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS = dependencies.SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS
    warmup_minutes = 2
    cooldown_minutes = 3
    stop_before_end_minutes = 1
    min_samples_per_session = 3
    session_items = []
    for row in sessions:
        room_id = normalize_room_id(row.room_id)
        bounds = sunbed_session_bounds(row)
        if not room_id or not bounds:
            continue
        start_at, end_at = bounds
        session_items.append({'id': row.id, 'room_id': room_id, 'sun2_bed_id': row.sun2_bed_id, 'start': start_at, 'end': end_at, 'measure_start': start_at + timedelta(minutes=warmup_minutes), 'measure_end': end_at - timedelta(minutes=stop_before_end_minutes), 'occupied_end': end_at + timedelta(minutes=cooldown_minutes), 'duration_minutes': max(0.0, (end_at - start_at).total_seconds() / 60)})
    events = []
    sessions_by_id = {}
    for item in session_items:
        sessions_by_id[item['id']] = item
        events.append((item['start'], 1, item['id']))
        events.append((item['occupied_end'], -1, item['id']))
    events.sort(key=lambda item: (item[0], item[1]))
    ventilation_items: list[tuple[datetime, bool]] = []
    for row in ventilation_samples or []:
        bucket = row.get('bucket_start') if isinstance(row, dict) else getattr(row, 'bucket_start', None)
        bucket = normalize_local_naive(bucket)
        fan_tak = row.get('fan_tak') if isinstance(row, dict) else getattr(row, 'fan_tak', None)
        if bucket is not None:
            ventilation_items.append((bucket, bool(fan_tak)))
    ventilation_items.sort(key=lambda item: item[0])
    sample_items: list[tuple[datetime, float]] = []
    for sample in samples:
        bucket = sample.get('bucket_start') if isinstance(sample, dict) else getattr(sample, 'bucket_start', None)
        bucket = normalize_local_naive(bucket)
        value = sample.get('differanse_beregnet_w') if isinstance(sample, dict) else getattr(sample, 'differanse_beregnet_w', None)
        try:
            diff_w = float(value)
        except (TypeError, ValueError):
            continue
        if bucket is not None:
            sample_items.append((bucket, diff_w))
    sample_items.sort(key=lambda item: item[0])
    sample_interval_candidates = [(right[0] - left[0]).total_seconds() for left, right in zip(sample_items, sample_items[1:]) if 5 <= (right[0] - left[0]).total_seconds() <= 300]
    sample_interval_seconds = float(median(sample_interval_candidates)) if sample_interval_candidates else 30.0
    active: set[int] = set()
    event_index = 0
    ventilation_index = 0
    single_samples: list[tuple[datetime, float, float, int]] = []
    baseline_by_day_hour: Dict[tuple[date, int], list[float]] = defaultdict(list)
    baseline_by_day: Dict[date, list[float]] = defaultdict(list)
    baseline_global: list[float] = []
    overlap_samples = 0
    roof_exhaust_adjusted_samples = 0
    for sample_time, diff_w in sample_items:
        while ventilation_index < len(ventilation_items) and ventilation_items[ventilation_index][0] < sample_time:
            ventilation_index += 1
        ventilation_candidates = []
        if ventilation_index < len(ventilation_items):
            ventilation_candidates.append(ventilation_items[ventilation_index])
        if ventilation_index > 0:
            ventilation_candidates.append(ventilation_items[ventilation_index - 1])
        adjustment_w = 0.0
        if ventilation_candidates:
            nearest_time, nearest_fan_tak = min(ventilation_candidates, key=lambda item: abs((sample_time - item[0]).total_seconds()))
            if nearest_fan_tak and abs((sample_time - nearest_time).total_seconds()) <= SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS:
                adjustment_w = ROOF_EXHAUST_UNMETERED_W
                roof_exhaust_adjusted_samples += 1
        analysis_diff_w = diff_w - adjustment_w
        while event_index < len(events) and events[event_index][0] <= sample_time:
            _, action, session_id = events[event_index]
            if action == 1:
                active.add(session_id)
            else:
                active.discard(session_id)
            event_index += 1
        if len(active) == 0:
            baseline_by_day_hour[sample_time.date(), sample_time.hour].append(analysis_diff_w)
            baseline_by_day[sample_time.date()].append(analysis_diff_w)
            baseline_global.append(analysis_diff_w)
        elif len(active) == 1:
            single_samples.append((sample_time, diff_w, analysis_diff_w, next(iter(active))))
        else:
            overlap_samples += 1
    global_baseline = median(baseline_global) if baseline_global else None
    baseline_by_day_hour_median = {key: median(values) for key, values in baseline_by_day_hour.items() if values}
    baseline_by_day_median = {key: median(values) for key, values in baseline_by_day.items() if values}
    per_room: Dict[str, Dict[str, Any]] = {}
    per_session: Dict[int, Dict[str, Any]] = {}
    candidate_sessions: Dict[int, Dict[str, Any]] = {}
    used_samples = 0
    rejected_low = 0
    missing_baseline = 0
    rejected_warmup_cooldown = 0
    rejected_short_sessions = 0
    rejected_short_samples = 0
    for sample_time, diff_w, analysis_diff_w, session_id in single_samples:
        session_item = sessions_by_id.get(session_id)
        if not session_item:
            continue
        if not session_item['measure_start'] <= sample_time < session_item['measure_end']:
            rejected_warmup_cooldown += 1
            continue
        baseline = baseline_by_day_hour_median.get((sample_time.date(), sample_time.hour))
        if baseline is None:
            baseline = baseline_by_day_median.get(sample_time.date(), global_baseline)
        if baseline is None:
            missing_baseline += 1
            continue
        net_w = analysis_diff_w - baseline
        if net_w <= 500:
            rejected_low += 1
            continue
        if session_id not in candidate_sessions:
            candidate_sessions[session_id] = {**session_item, 'net_values': [], 'observed_values': [], 'baseline_values': []}
        candidate_sessions[session_id]['net_values'].append(net_w)
        candidate_sessions[session_id]['observed_values'].append(diff_w)
        candidate_sessions[session_id]['baseline_values'].append(baseline)
    for session_id, session_item in candidate_sessions.items():
        net_values = session_item['net_values']
        if len(net_values) < min_samples_per_session:
            rejected_short_sessions += 1
            rejected_short_samples += len(net_values)
            continue
        room_id = session_item['room_id']
        bed = bed_lookup.get(room_id)
        if room_id not in per_room:
            per_room[room_id] = {'room_id': room_id, 'label': sun2_room_label(room_id, getattr(bed, 'name', None) if bed else None), 'sun2_bed_id': getattr(bed, 'sun2_bed_id', None) if bed else session_item.get('sun2_bed_id'), 'bed_model': getattr(bed, 'bed_model', None) if bed else None, 'samples_count': 0, 'sessions': set(), 'net_values': [], 'observed_values': [], 'baseline_values': [], 'estimated_kwh': 0.0, 'duration_minutes': 0.0}
        target = per_room[room_id]
        target['samples_count'] += len(net_values)
        target['sessions'].add(session_id)
        target['net_values'].extend(net_values)
        target['observed_values'].extend(session_item['observed_values'])
        target['baseline_values'].extend(session_item['baseline_values'])
        target['estimated_kwh'] += sum(net_values) * sample_interval_seconds / 3600 / 1000
        used_samples += len(net_values)
        per_session[session_id] = {**session_item, 'label': target['label'], 'net_values': list(net_values), 'observed_values': list(session_item['observed_values']), 'baseline_values': list(session_item['baseline_values'])}
    rooms = []
    for item in per_room.values():
        net_values = item.pop('net_values')
        observed_values = item.pop('observed_values')
        baseline_values = item.pop('baseline_values')
        session_count = len(item.pop('sessions'))
        avg_w = sum(net_values) / len(net_values) if net_values else None
        median_w = median(net_values) if net_values else None
        estimate_w = median_w
        item.update({'sessions_count': session_count, 'avg_w': avg_w, 'median_w': median_w, 'estimate_w': estimate_w, 'p25_w': percentile(net_values, 0.25), 'p75_w': percentile(net_values, 0.75), 'min_w': min(net_values) if net_values else None, 'max_w': max(net_values) if net_values else None, 'avg_observed_w': sum(observed_values) / len(observed_values) if observed_values else None, 'avg_baseline_w': sum(baseline_values) / len(baseline_values) if baseline_values else None, 'kwh_10_min': (estimate_w or 0) / 1000 * (10 / 60), 'kwh_15_min': (estimate_w or 0) / 1000 * (15 / 60), 'kwh_20_min': (estimate_w or 0) / 1000 * (20 / 60), 'confidence': 'H�y' if len(net_values) >= 60 and session_count >= 5 else 'Middels' if len(net_values) >= 20 and session_count >= 2 else 'Lav'})
        rooms.append(item)
    rooms.sort(key=lambda item: item.get('room_id') or '')
    observations = []
    for item in per_session.values():
        net_values = item['net_values']
        if not net_values:
            continue
        observations.append({'session_id': item['id'], 'room_id': item['room_id'], 'label': item['label'], 'start': item['start'], 'end': item['end'], 'duration_minutes': item['duration_minutes'], 'samples_count': len(net_values), 'avg_w': sum(net_values) / len(net_values), 'median_w': median(net_values), 'avg_observed_w': sum(item['observed_values']) / len(item['observed_values']), 'avg_baseline_w': sum(item['baseline_values']) / len(item['baseline_values']), 'estimated_kwh': sum(net_values) * sample_interval_seconds / 3600 / 1000})
    observations.sort(key=lambda item: item['start'], reverse=True)
    return {'rooms': rooms, 'observations': observations[:80], 'summary': {'sessions_total': len(session_items), 'energy_samples_total': len(sample_items), 'roof_exhaust_adjusted_samples': roof_exhaust_adjusted_samples, 'roof_exhaust_adjustment_w': ROOF_EXHAUST_UNMETERED_W, 'baseline_samples': len(baseline_global), 'single_samples': used_samples, 'overlap_samples': overlap_samples, 'missing_baseline_samples': missing_baseline, 'rejected_low_samples': rejected_low, 'rejected_warmup_cooldown_samples': rejected_warmup_cooldown, 'rejected_short_sessions': rejected_short_sessions, 'rejected_short_samples': rejected_short_samples, 'global_baseline_w': global_baseline, 'rooms_count': len(rooms), 'warmup_minutes': warmup_minutes, 'cooldown_minutes': cooldown_minutes, 'stop_before_end_minutes': stop_before_end_minutes, 'min_samples_per_session': min_samples_per_session, 'sample_interval_seconds': sample_interval_seconds}}
