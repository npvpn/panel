import { useQuery } from "react-query";
import { fetch } from "service/http";

export const useNodeSettings = () => {
  return useQuery({
    queryKey: ["node-settings"],
    queryFn: () =>
      fetch<{
        min_node_version: string;
        certificate: string;
      }>("/node/settings"),
  });
};
