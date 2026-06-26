import { Input } from "antd";

type TableSearchProps = {
  value: string;
  placeholder: string;
  className?: string;
  buttonLabel?: string;
  onValueChange: (value: string) => void;
  onSearch: (value?: string) => void;
  onClear: () => void;
};

export function TableSearch({
  value,
  placeholder,
  className = "table-toolbar",
  buttonLabel = "Søk",
  onValueChange,
  onSearch,
  onClear,
}: TableSearchProps) {
  return (
    <div className={className}>
      <Input.Search
        allowClear
        placeholder={placeholder}
        value={value}
        onChange={(event) => {
          const nextValue = event.target.value;
          onValueChange(nextValue);
          if (!nextValue) onClear();
        }}
        onSearch={onSearch}
        enterButton={buttonLabel}
      />
    </div>
  );
}
