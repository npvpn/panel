import { fetch } from "./http";

export type MasterInbounds = { inbounds: string[] };

export const getMasterInbounds = () =>
  fetch<MasterInbounds>("/master/inbounds");

export const setMasterInbounds = (inbounds: string[]) =>
  fetch<MasterInbounds>("/master/inbounds", { method: "PUT", body: { inbounds } });
