export type Bot = {
  id: number;
  username: string;
  title?: string | null;
};

export type BotSettings = {
  sub_update_interval: string;
  sub_support_url: string;
  sub_profile_title: string;
  sub_routing_happ: string;
  sub_routing_v2raytun: string;
  sub_client_note: string;
  sub_profile_url: string;
  bot_url: string;
  sub_revoked_announce_text: string;
  sub_expired_announce_text: string;
  sub_device_limit_announce_text: string;
  sub_unsupported_client_announce_text: string;
  sub_revoked_server_text: string[];
  sub_expired_server_text: string[];
  sub_device_limit_server_text: string[];
  sub_unsupported_client_server_text: string[];
};
