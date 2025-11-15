import React, { useState, useEffect } from "react";
import { isAdminRole } from "@/utils/roles";
import CustomersHeaderTabs from "@/app/(dashboard)/customers/components/CustomersHeaderTabs";
import CustomersListPanel from "@/app/(dashboard)/customers/components/CustomersListPanel";
import CustomersSpendPanel from "@/app/(dashboard)/customers/components/CustomersSpendPanel";
import { TabPanel } from "@tremor/react";
import { allEndUsersCall } from "@/components/networking";

interface Customer {
  user_id: string;
  alias: string | null;
  spend: number;
  blocked: boolean;
  allowed_model_region: string | null;
  default_model: string | null;
  budget_id: string | null;
  litellm_budget_table?: any;
}

interface CustomersViewProps {
  accessToken: string | null;
  userID: string | null;
  userRole: string | null;
}

const CustomersView: React.FC<CustomersViewProps> = ({
  accessToken,
  userID,
  userRole,
}) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  const fetchCustomers = async () => {
    if (!accessToken || !isAdminRole(userRole || "")) {
      return;
    }

    setLoading(true);
    try {
      const data = await allEndUsersCall(accessToken);
      setCustomers(data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Failed to fetch customers:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [accessToken, userRole]);

  const handleRefresh = () => {
    fetchCustomers();
  };

  // Check if user is admin
  if (!isAdminRole(userRole || "")) {
    return (
      <div className="p-8">
        <p className="text-red-500">
          Access denied. This page is only available to administrators.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-semibold mb-4">Customer Management</h1>
      <CustomersHeaderTabs
        lastRefreshed={lastRefreshed}
        onRefresh={handleRefresh}
        userRole={userRole}
      >
        <TabPanel>
          <CustomersListPanel
            customers={customers}
            loading={loading}
            accessToken={accessToken}
            onRefresh={fetchCustomers}
          />
        </TabPanel>
        <TabPanel>
          <CustomersSpendPanel
            accessToken={accessToken}
            userRole={userRole}
          />
        </TabPanel>
      </CustomersHeaderTabs>
    </div>
  );
};

export default CustomersView;
