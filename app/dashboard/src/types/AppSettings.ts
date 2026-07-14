export type PlatformKey =
  | "ios"
  | "macos"
  | "android"
  | "androidtv"
  | "windows"
  | "linux";

export const PLATFORM_KEYS: PlatformKey[] = [
  "ios",
  "macos",
  "android",
  "androidtv",
  "windows",
  "linux",
];

export type LinkKey =
  | "ios_ru"
  | "ios_global"
  | "macos_ru"
  | "macos_global"
  | "android"
  | "androidtv"
  | "windows"
  | "linux";

export const LINK_KEYS: LinkKey[] = [
  "ios_ru",
  "ios_global",
  "macos_ru",
  "macos_global",
  "android",
  "androidtv",
  "windows",
  "linux",
];

export type ClientApp = {
  id: string;
  name: string;
  scheme: string;
  enabled: boolean;
  links: Record<LinkKey, string>;
};

export type ClientAppsSettings = {
  apps: ClientApp[];
  primary_by_platform: Partial<Record<PlatformKey, string>>;
};
