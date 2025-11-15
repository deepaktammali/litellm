import { Icon, Tab, TabGroup, TabList, TabPanels, Text } from "@tremor/react";
import { RefreshIcon } from "@heroicons/react/outline";
import React from "react";

type CustomersHeaderTabsProps = {
  lastRefreshed: string;
  onRefresh: () => void;
  userRole: string | null;
  children: React.ReactNode;
};

const CustomersHeaderTabs = ({ lastRefreshed, onRefresh, userRole, children }: CustomersHeaderTabsProps) => {
  return (
    <TabGroup className="gap-2 h-[75vh] w-full">
      <TabList className="flex justify-between mt-2 w-full items-center">
        <div className="flex">
          <Tab>Customer List</Tab>
          <Tab>Usage & Spend</Tab>
        </div>
        <div className="flex items-center space-x-2">
          {lastRefreshed && <Text>Last Refreshed: {lastRefreshed}</Text>}
          <Icon
            icon={RefreshIcon}
            variant="shadow"
            size="xs"
            className="self-center cursor-pointer"
            onClick={onRefresh}
          />
        </div>
      </TabList>
      <TabPanels>{children}</TabPanels>
    </TabGroup>
  );
};

export default CustomersHeaderTabs;
