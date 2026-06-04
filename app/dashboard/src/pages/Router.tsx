import { createHashRouter } from "react-router-dom";
import { fetch } from "../service/http";
import { getAuthToken } from "../utils/authStorage";
import { Dashboard } from "./Dashboard";
import { Login } from "./Login";
const fetchAdminLoader = () => {
  // return fetch("/admin", {
  //   headers: {
  //     Authorization: `Bearer ${getAuthToken()}`,
  //   },
  // });
  return Promise.resolve({ username: "admin" });
};
export const router = createHashRouter([
  {
    path: "/",
    element: <Dashboard />,
    // errorElement: <Login />,
    loader: fetchAdminLoader,
  },
  {
    path: "/login/",
    element: <Login />,
  },
]);
