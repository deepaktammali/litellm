"use client";

import CustomersView from "@/app/(dashboard)/customers/CustomersView";
import useAuthorized from "@/app/(dashboard)/hooks/useAuthorized";

const CustomersPage = () => {
  const { accessToken, userId, userRole } = useAuthorized();

  return (
    <CustomersView
      accessToken={accessToken}
      userID={userId}
      userRole={userRole}
    />
  );
};

export default CustomersPage;
