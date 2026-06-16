import { useQuery } from "react-query";
import { fetch } from "service/http";
import { z } from "zod";
import { create } from "zustand";
import { FilterUsageType, useDashboard } from "./DashboardContext";

export const NodeSchema = z.object({
  name: z.string().min(1),
  address: z.string().min(1),
  port: z
    .number()
    .min(1)
    .or(z.string().transform((v) => parseFloat(v))),
  api_port: z
    .number()
    .min(1)
    .or(z.string().transform((v) => parseFloat(v))),
  protocol: z.enum(["rest", "rpyc"]),
  xray_version: z.string().nullable().optional(),
  id: z.number().nullable().optional(),
  status: z
    .enum(["connected", "connecting", "error", "disabled"])
    .nullable()
    .optional(),
  message: z.string().nullable().optional(),
  add_as_new_host: z.boolean().optional(),
  usage_coefficient: z.number().or(z.string().transform((v) => parseFloat(v))),
  inbounds: z.array(z.string()).optional(),
  role: z.enum(["entry", "exit", "direct"]).optional(),
  cascade_routes: z
    .array(
      z.object({
        exit_node_id: z.number().min(1),
        entry_inbound_tag: z.string().min(1),
        cascade_inbound_tag: z.string().min(1),
      })
    )
    .optional(),
  is_bs: z.boolean().optional(),
  bs_daily_limit: z.number().nullable().optional(),
  bs_monthly_limit: z.number().nullable().optional(),
});

export type NodeType = z.infer<typeof NodeSchema>;

export const getNodeDefaultValues = (): NodeType => ({
  name: "",
  address: "",
  port: 62050,
  api_port: 62051,
  protocol: "rest",
  xray_version: "",
  usage_coefficient: 1,
  inbounds: [],
  role: "direct",
  cascade_routes: [],
  is_bs: false,
  bs_daily_limit: null,
  bs_monthly_limit: null,
});

export const FetchNodesQueryKey = "fetch-nodes-query-key";

export type NodeStore = {
  nodes: NodeType[];
  addNode: (node: NodeType) => Promise<unknown>;
  fetchNodes: () => Promise<NodeType[]>;
  fetchNodesUsage: (query: FilterUsageType) => Promise<void>;
  updateNode: (node: NodeType) => Promise<unknown>;
  reconnectNode: (node: NodeType) => Promise<unknown>;
  deletingNode?: NodeType | null;
  deleteNode: () => Promise<unknown>;
  setDeletingNode: (node: NodeType | null) => void;
};

export const useNodesQuery = () => {
  const { isEditingNodes } = useDashboard();
  return useQuery({
    queryKey: FetchNodesQueryKey,
    queryFn: useNodes.getState().fetchNodes,
    refetchInterval: isEditingNodes ? 3000 : undefined,
    refetchOnWindowFocus: false,
  });
};

export const useNodes = create<NodeStore>((set, get) => ({
  nodes: [],
  addNode(body) {
    return fetch("/node", { method: "POST", body });
  },
  fetchNodes() {
    return fetch("/nodes");
  },
  fetchNodesUsage(query: FilterUsageType) {
    return fetch("/nodes/usage", { query });
  },
  updateNode(body) {
    return fetch(`/node/${body.id}`, {
      method: "PUT",
      body,
    });
  },
  setDeletingNode(node) {
    set({ deletingNode: node });
  },
  reconnectNode(body) {
    return fetch(`/node/${body.id}/reconnect`, {
      method: "POST",
    });
  },
  deleteNode: () => {
    return fetch(`/node/${get().deletingNode?.id}`, {
      method: "DELETE",
    });
  },
}));
