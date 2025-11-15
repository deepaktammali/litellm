import React, { useState } from "react";
import {
  Table,
  TableHead,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
  Badge,
  Card,
  Text,
  Button,
} from "@tremor/react";
import { Spin } from "antd";

interface Customer {
  user_id: string;
  alias: string | null;
  spend: number;
  blocked: boolean;
  allowed_model_region: string | null;
  default_model: string | null;
  budget_id: string | null;
  litellm_budget_table?: {
    max_budget: number | null;
  };
}

interface CustomersListPanelProps {
  customers: Customer[];
  loading: boolean;
  accessToken: string | null;
  onRefresh: () => void;
}

const CustomersListPanel: React.FC<CustomersListPanelProps> = ({
  customers,
  loading,
  accessToken,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredCustomers = customers.filter(
    (customer) =>
      customer.user_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (customer.alias && customer.alias.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <Card className="h-full overflow-auto">
      <div className="mb-4 flex justify-between items-center">
        <div>
          <Text className="text-lg font-semibold">Customers</Text>
          <Text className="text-sm text-gray-500">
            Total: {filteredCustomers.length} {filteredCustomers.length !== customers.length && `(filtered from ${customers.length})`}
          </Text>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search by ID or alias..."
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Spin size="large" />
        </div>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>User ID</TableHeaderCell>
              <TableHeaderCell>Alias</TableHeaderCell>
              <TableHeaderCell>Spend</TableHeaderCell>
              <TableHeaderCell>Budget</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell>Region</TableHeaderCell>
              <TableHeaderCell>Default Model</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredCustomers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <Text>No customers found</Text>
                </TableCell>
              </TableRow>
            ) : (
              filteredCustomers.map((customer) => (
                <TableRow key={customer.user_id}>
                  <TableCell>
                    <Text className="font-mono text-sm">{customer.user_id}</Text>
                  </TableCell>
                  <TableCell>
                    <Text>{customer.alias || "-"}</Text>
                  </TableCell>
                  <TableCell>
                    <Text className="font-semibold">{formatCurrency(customer.spend)}</Text>
                  </TableCell>
                  <TableCell>
                    <Text>
                      {customer.litellm_budget_table?.max_budget
                        ? formatCurrency(customer.litellm_budget_table.max_budget)
                        : "-"}
                    </Text>
                  </TableCell>
                  <TableCell>
                    {customer.blocked ? (
                      <Badge color="red">Blocked</Badge>
                    ) : (
                      <Badge color="green">Active</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Text>{customer.allowed_model_region || "-"}</Text>
                  </TableCell>
                  <TableCell>
                    <Text className="text-sm">{customer.default_model || "-"}</Text>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}
    </Card>
  );
};

export default CustomersListPanel;
