import React, { useState, useEffect } from "react";
import {
  Table,
  TableHead,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
  Card,
  Text,
  Button,
  Title,
  Metric,
  Grid,
  Col,
} from "@tremor/react";
import { Spin, DatePicker } from "antd";
import { customerSpendReportCall } from "@/components/networking";
import dayjs, { Dayjs } from "dayjs";

const { RangePicker } = DatePicker;

interface SpendByModel {
  [model: string]: {
    spend: number;
    requests: number;
    tokens: number;
  };
}

interface CustomerSpendRecord {
  user_id: string;
  alias: string | null;
  total_spend: number;
  total_requests: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  spend_by_model: SpendByModel;
}

interface SpendReportData {
  spend_report: CustomerSpendRecord[];
  total_customers: number;
  date_range: {
    start_date: string | null;
    end_date: string | null;
  };
}

interface CustomersSpendPanelProps {
  accessToken: string | null;
  userRole: string | null;
}

const CustomersSpendPanel: React.FC<CustomersSpendPanelProps> = ({
  accessToken,
  userRole,
}) => {
  const [loading, setLoading] = useState(false);
  const [spendData, setSpendData] = useState<SpendReportData | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([
    dayjs().subtract(30, "days"),
    dayjs(),
  ]);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const fetchSpendReport = async () => {
    if (!accessToken) return;

    setLoading(true);
    try {
      const startDate = dateRange[0]?.format("YYYY-MM-DD");
      const endDate = dateRange[1]?.format("YYYY-MM-DD");

      const data = await customerSpendReportCall(
        accessToken,
        startDate,
        endDate
      );
      setSpendData(data);
    } catch (error) {
      console.error("Failed to fetch customer spend report:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSpendReport();
  }, [accessToken]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(num);
  };

  const toggleRowExpansion = (userId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(userId)) {
      newExpanded.delete(userId);
    } else {
      newExpanded.add(userId);
    }
    setExpandedRows(newExpanded);
  };

  const totalSpend = spendData?.spend_report.reduce((sum, record) => sum + record.total_spend, 0) || 0;
  const totalRequests = spendData?.spend_report.reduce((sum, record) => sum + record.total_requests, 0) || 0;
  const totalTokens = spendData?.spend_report.reduce((sum, record) => sum + record.total_tokens, 0) || 0;

  return (
    <Card className="h-full overflow-auto">
      <div className="mb-6">
        <Title>Customer Usage & Spend Report</Title>
        <Text className="text-gray-500">
          View detailed spend breakdown for all customers
        </Text>
      </div>

      <div className="mb-6 flex gap-4 items-end">
        <div>
          <Text className="mb-2 font-medium">Date Range</Text>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [Dayjs | null, Dayjs | null])}
            format="YYYY-MM-DD"
          />
        </div>
        <Button onClick={fetchSpendReport} disabled={loading}>
          Apply Filter
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Spin size="large" />
        </div>
      ) : (
        <>
          <Grid numItemsMd={3} numItemsLg={3} className="gap-6 mb-6">
            <Card decoration="top" decorationColor="blue">
              <Text>Total Spend</Text>
              <Metric>{formatCurrency(totalSpend)}</Metric>
            </Card>
            <Card decoration="top" decorationColor="green">
              <Text>Total Requests</Text>
              <Metric>{formatNumber(totalRequests)}</Metric>
            </Card>
            <Card decoration="top" decorationColor="purple">
              <Text>Total Tokens</Text>
              <Metric>{formatNumber(totalTokens)}</Metric>
            </Card>
          </Grid>

          {spendData && spendData.spend_report.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell></TableHeaderCell>
                    <TableHeaderCell>User ID</TableHeaderCell>
                    <TableHeaderCell>Alias</TableHeaderCell>
                    <TableHeaderCell className="text-right">Total Spend</TableHeaderCell>
                    <TableHeaderCell className="text-right">Requests</TableHeaderCell>
                    <TableHeaderCell className="text-right">Tokens</TableHeaderCell>
                    <TableHeaderCell className="text-right">Prompt Tokens</TableHeaderCell>
                    <TableHeaderCell className="text-right">Completion Tokens</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {spendData.spend_report.map((record) => (
                    <React.Fragment key={record.user_id}>
                      <TableRow className="hover:bg-gray-50 cursor-pointer" onClick={() => toggleRowExpansion(record.user_id)}>
                        <TableCell>
                          <Text className="text-blue-600">
                            {expandedRows.has(record.user_id) ? "▼" : "▶"}
                          </Text>
                        </TableCell>
                        <TableCell>
                          <Text className="font-mono text-sm">{record.user_id}</Text>
                        </TableCell>
                        <TableCell>
                          <Text className="font-medium">{record.alias || "-"}</Text>
                        </TableCell>
                        <TableCell className="text-right">
                          <Text className="font-semibold">{formatCurrency(record.total_spend)}</Text>
                        </TableCell>
                        <TableCell className="text-right">
                          <Text>{formatNumber(record.total_requests)}</Text>
                        </TableCell>
                        <TableCell className="text-right">
                          <Text>{formatNumber(record.total_tokens)}</Text>
                        </TableCell>
                        <TableCell className="text-right">
                          <Text>{formatNumber(record.total_prompt_tokens)}</Text>
                        </TableCell>
                        <TableCell className="text-right">
                          <Text>{formatNumber(record.total_completion_tokens)}</Text>
                        </TableCell>
                      </TableRow>
                      {expandedRows.has(record.user_id) && (
                        <TableRow>
                          <TableCell colSpan={8} className="bg-gray-50 p-4">
                            <div className="ml-8">
                              <Text className="font-semibold mb-2">Model Breakdown</Text>
                              <Table className="mt-2">
                                <TableHead>
                                  <TableRow>
                                    <TableHeaderCell>Model</TableHeaderCell>
                                    <TableHeaderCell className="text-right">Spend</TableHeaderCell>
                                    <TableHeaderCell className="text-right">Requests</TableHeaderCell>
                                    <TableHeaderCell className="text-right">Tokens</TableHeaderCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {Object.entries(record.spend_by_model).map(([model, stats]) => (
                                    <TableRow key={model}>
                                      <TableCell>
                                        <Text className="font-mono text-sm">{model}</Text>
                                      </TableCell>
                                      <TableCell className="text-right">
                                        <Text>{formatCurrency(stats.spend)}</Text>
                                      </TableCell>
                                      <TableCell className="text-right">
                                        <Text>{formatNumber(stats.requests)}</Text>
                                      </TableCell>
                                      <TableCell className="text-right">
                                        <Text>{formatNumber(stats.tokens)}</Text>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Text className="text-gray-500">
                No spend data available for the selected date range
              </Text>
            </div>
          )}
        </>
      )}
    </Card>
  );
};

export default CustomersSpendPanel;
