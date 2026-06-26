import { Card, Table, Typography } from "antd";
import type { CardProps, TableProps } from "antd";
import type { ReactNode } from "react";

type DataTableCardProps<T extends object> = TableProps<T> & {
  cardTitle?: ReactNode;
  className?: string;
  note?: ReactNode;
  cardProps?: Omit<CardProps, "title" | "className">;
};

export function DataTableCard<T extends object>({
  cardTitle,
  className = "",
  note,
  cardProps,
  ...tableProps
}: DataTableCardProps<T>) {
  return (
    <Card {...cardProps} className={`table-card ${className}`.trim()} title={cardTitle}>
      <Table<T> {...tableProps} />
      {note ? (
        <Typography.Text type="secondary" className="table-note">
          {note}
        </Typography.Text>
      ) : null}
    </Card>
  );
}
