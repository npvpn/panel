import {
  Box,
  Button,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Switch,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Textarea,
  useToast,
  VStack,
  Text as ChakraText,
  useOutsideClick,
} from "@chakra-ui/react";
import { FC, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDashboard } from "contexts/DashboardContext";
import { fetch } from "service/http";
import { Bot, BotSettings } from "types/Bot";

const GB_IN_BYTES = 1073741824;

const toText = (values: string[] = []) => values.join("\n");

const toList = (value: string) =>
  value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

const emptySettings: BotSettings = {
  sub_update_interval: "",
  sub_support_url: "",
  sub_profile_title: "",
  sub_routing_happ: "",
  sub_routing_v2raytun: "",
  sub_client_note: "",
  sub_profile_url: "",
  bot_url: "",
  web_url: "",
  sub_revoked_announce_text: "",
  sub_expired_announce_text: "",
  sub_device_limit_announce_text: "",
  sub_device_limit_hard_mode: false,
  sub_unsupported_client_announce_text: "",
  sub_revoked_server_text: [],
  sub_expired_server_text: [],
  sub_device_limit_server_text: [],
  sub_unsupported_client_server_text: [],
  sub_bs_limit_server_text: [],
  sub_bs_limit_announce_text: "",
  sub_v2ray_json_template: "",
  sub_routing_json_default: "",
  sub_routing_json_bs: "",
  bs_daily_limit: 0,
  bs_monthly_limit: 0,
};

type ServerTextField =
  | "sub_revoked_server_text"
  | "sub_expired_server_text"
  | "sub_device_limit_server_text"
  | "sub_unsupported_client_server_text"
  | "sub_bs_limit_server_text";

type ListFieldTexts = Record<ServerTextField, string>;

const toListFieldTexts = (settings: BotSettings): ListFieldTexts => ({
  sub_revoked_server_text: toText(settings.sub_revoked_server_text),
  sub_expired_server_text: toText(settings.sub_expired_server_text),
  sub_device_limit_server_text: toText(settings.sub_device_limit_server_text),
  sub_unsupported_client_server_text: toText(
    settings.sub_unsupported_client_server_text
  ),
  sub_bs_limit_server_text: toText(settings.sub_bs_limit_server_text),
});

export const BotSettingsDialog: FC = () => {
  const { isEditingBotSettings, onEditingBotSettings } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();
  const [bots, setBots] = useState<Bot[]>([]);
  const [selectedBot, setSelectedBot] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [defaultSettings, setDefaultSettings] =
    useState<BotSettings>(emptySettings);
  const [botUsername, setBotUsername] = useState("");
  const [botTitle, setBotTitle] = useState("");
  const [settings, setSettings] = useState<BotSettings>(emptySettings);
  const [hasDraft, setHasDraft] = useState(false);
  const [botSearch, setBotSearch] = useState("");
  const [isBotListOpen, setIsBotListOpen] = useState(false);
  const [listFieldTexts, setListFieldTexts] = useState<ListFieldTexts>(
    toListFieldTexts(emptySettings)
  );
  const botSelectorRef = useRef<HTMLDivElement>(null);

  useOutsideClick({
    ref: botSelectorRef,
    handler: () => setIsBotListOpen(false),
  });

  const NEW_BOT_DRAFT_KEY = "botSettings_draft_new";

  const getDraftKey = (username: string) =>
    username ? `botSettings_draft_${username}` : NEW_BOT_DRAFT_KEY;

  const saveDraftTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const saveDraft = (
    newSettings: BotSettings,
    newUsername: string,
    newTitle: string
  ) => {
    const key = getDraftKey(selectedBot);
    if (saveDraftTimeout.current) clearTimeout(saveDraftTimeout.current);
    saveDraftTimeout.current = setTimeout(() => {
      localStorage.setItem(
        key,
        JSON.stringify({
          settings: newSettings,
          botUsername: newUsername,
          botTitle: newTitle,
          savedAt: Date.now(),
        })
      );
    }, 400);
  };

  const updateSettings = (patch: Partial<BotSettings>) => {
    const s = { ...settings, ...patch };
    setSettings(s);
    saveDraft(s, botUsername, botTitle);
  };

  const replaceSettings = (nextSettings: BotSettings) => {
    setSettings(nextSettings);
    setListFieldTexts(toListFieldTexts(nextSettings));
  };

  const updateListField = (field: ServerTextField, value: string) => {
    setListFieldTexts((current) => ({ ...current, [field]: value }));
    updateSettings({ [field]: toList(value) });
  };

  const fetchBots = () => {
    return fetch<Bot[]>("/bots")
      .then((items) => {
        setBots(items);
      })
      .catch(() => {
        setBots([]);
      });
  };

  useEffect(() => {
    return () => {
      if (saveDraftTimeout.current) clearTimeout(saveDraftTimeout.current);
    };
  }, []);

  useEffect(() => {
    if (!isEditingBotSettings) return;
    setLoading(true);
    setSelectedBot("");
    setBotUsername("");
    setBotTitle("");
    setBotSearch("");
    replaceSettings(emptySettings);
    Promise.all([
      fetchBots(),
      fetch<BotSettings>("/bots/default-settings").then(setDefaultSettings),
    ]).finally(() => setLoading(false));
  }, [isEditingBotSettings]);

  useEffect(() => {
    if (!isEditingBotSettings) return;

    if (saveDraftTimeout.current) clearTimeout(saveDraftTimeout.current);

    if (!selectedBot) {
      setBotUsername("");
      setBotTitle("");
      replaceSettings(emptySettings);
      const newDraft = localStorage.getItem(NEW_BOT_DRAFT_KEY);
      setHasDraft(!!newDraft);
      return;
    }
    const selected = bots.find((bot) => bot.username === selectedBot);
    setBotUsername(selected?.username || "");
    setBotTitle(selected?.title || "");
    setLoading(true);

    let cancelled = false;

    fetch<BotSettings>(`/bots/${selectedBot}/settings`)
      .then((serverSettings) => {
        if (cancelled) return;
        replaceSettings(serverSettings);

        const draftKey = getDraftKey(selectedBot);
        const draft = localStorage.getItem(draftKey);

        if (draft) {
          setHasDraft(true);
        } else {
          setHasDraft(false);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isEditingBotSettings, selectedBot, bots]);

  useEffect(() => {
    if (!selectedBot) {
      setBotSearch("");
      return;
    }

    setBotSearch(`@${selectedBot}`);
  }, [selectedBot]);

  const restoreDraft = () => {
    const key = getDraftKey(selectedBot);
    const draft = localStorage.getItem(key);
    if (!draft) return;
    const parsed = JSON.parse(draft);
    replaceSettings(parsed.settings);
    setBotUsername(parsed.botUsername);
    setBotTitle(parsed.botTitle);
    localStorage.removeItem(key);
    setHasDraft(false);
  };

  const discardDraft = () => {
    localStorage.removeItem(getDraftKey(selectedBot));
    setHasDraft(false);
  };

  const close = () => onEditingBotSettings(false);

  const selectedBotModel = useMemo(
    () => bots.find((bot) => bot.username === selectedBot),
    [bots, selectedBot]
  );

  const mergeWithDefaults = (current: BotSettings): BotSettings => {
    return {
      sub_update_interval:
        current.sub_update_interval.trim() ||
        defaultSettings.sub_update_interval,
      sub_support_url:
        current.sub_support_url.trim() || defaultSettings.sub_support_url,
      sub_profile_title:
        current.sub_profile_title.trim() || defaultSettings.sub_profile_title,
      sub_routing_happ:
        current.sub_routing_happ.trim() || defaultSettings.sub_routing_happ,
      sub_routing_v2raytun:
        current.sub_routing_v2raytun.trim() ||
        defaultSettings.sub_routing_v2raytun,
      sub_client_note:
        current.sub_client_note.trim() || defaultSettings.sub_client_note,
      sub_profile_url:
        current.sub_profile_url.trim() || defaultSettings.sub_profile_url,
      bot_url: current.bot_url.trim() || defaultSettings.bot_url,
      web_url: current.web_url.trim() || defaultSettings.web_url,
      sub_revoked_announce_text:
        current.sub_revoked_announce_text.trim() ||
        defaultSettings.sub_revoked_announce_text,
      sub_expired_announce_text:
        current.sub_expired_announce_text.trim() ||
        defaultSettings.sub_expired_announce_text,
      sub_device_limit_announce_text:
        current.sub_device_limit_announce_text.trim() ||
        defaultSettings.sub_device_limit_announce_text,
      sub_device_limit_hard_mode: current.sub_device_limit_hard_mode,
      sub_unsupported_client_announce_text:
        current.sub_unsupported_client_announce_text.trim() ||
        defaultSettings.sub_unsupported_client_announce_text,
      sub_revoked_server_text:
        current.sub_revoked_server_text.length > 0
          ? current.sub_revoked_server_text
          : defaultSettings.sub_revoked_server_text,
      sub_expired_server_text:
        current.sub_expired_server_text.length > 0
          ? current.sub_expired_server_text
          : defaultSettings.sub_expired_server_text,
      sub_device_limit_server_text:
        current.sub_device_limit_server_text.length > 0
          ? current.sub_device_limit_server_text
          : defaultSettings.sub_device_limit_server_text,
      sub_unsupported_client_server_text:
        current.sub_unsupported_client_server_text.length > 0
          ? current.sub_unsupported_client_server_text
          : defaultSettings.sub_unsupported_client_server_text,
      sub_bs_limit_server_text:
        current.sub_bs_limit_server_text.length > 0
          ? current.sub_bs_limit_server_text
          : defaultSettings.sub_bs_limit_server_text,
      sub_bs_limit_announce_text:
        current.sub_bs_limit_announce_text.trim() ||
        defaultSettings.sub_bs_limit_announce_text,
      sub_v2ray_json_template: current.sub_v2ray_json_template,
      sub_routing_json_default: current.sub_routing_json_default,
      sub_routing_json_bs: current.sub_routing_json_bs,
      bs_daily_limit: current.bs_daily_limit,
      bs_monthly_limit: current.bs_monthly_limit,
    };
  };

  const save = () => {
    if (!selectedBot) return;
    const normalizedUsername = botUsername.trim().replace(/^@/, "");
    if (!normalizedUsername) return;
    const normalizedTitle = botTitle.trim();
    const isIdentityChanged =
      normalizedUsername !== selectedBot ||
      normalizedTitle !== (selectedBotModel?.title || "");
    const settingsPayload = {
      ...settings,
      sub_revoked_server_text: toList(listFieldTexts.sub_revoked_server_text),
      sub_expired_server_text: toList(listFieldTexts.sub_expired_server_text),
      sub_device_limit_server_text: toList(
        listFieldTexts.sub_device_limit_server_text
      ),
      sub_unsupported_client_server_text: toList(
        listFieldTexts.sub_unsupported_client_server_text
      ),
      sub_bs_limit_server_text: toList(listFieldTexts.sub_bs_limit_server_text),
    };

    setSaving(true);
    let targetUsername = selectedBot;
    const identityPromise = isIdentityChanged
      ? fetch<Bot>(`/bots/${selectedBot}`, {
          method: "PATCH",
          body: {
            username: normalizedUsername,
            title: normalizedTitle || null,
          },
        }).then((updatedBot) => {
          targetUsername = updatedBot.username;
          setBotUsername(updatedBot.username);
          setBotTitle(updatedBot.title || "");
        })
      : Promise.resolve();

    identityPromise
      .then(() =>
        fetch<BotSettings>(`/bots/${targetUsername}/settings`, {
          method: "PUT",
          body: settingsPayload,
        })
      )
      .then((updated) => {
        replaceSettings(updated);
        return fetchBots().then(() => {
          setSelectedBot(targetUsername);
        });
      })
      .then(() => {
        localStorage.removeItem(getDraftKey(targetUsername));
        setHasDraft(false);
        toast({
          title: t("botSettings.saved"),
          status: "success",
          duration: 2500,
          isClosable: true,
          position: "top",
        });
      })
      .catch(() => {
        toast({
          title: t("core.generalErrorMessage"),
          status: "error",
          duration: 2500,
          isClosable: true,
          position: "top",
        });
      })
      .finally(() => setSaving(false));
  };

  const createBot = () => {
    if (!botUsername.trim()) return;
    setCreating(true);
    fetch<Bot>("/bots", {
      method: "POST",
      body: {
        username: botUsername.trim(),
        title: botTitle.trim() || null,
      },
    })
      .then((bot) => {
        return fetch<BotSettings>(`/bots/${bot.username}/settings`, {
          method: "PUT",
          body: mergeWithDefaults(settings),
        }).then(() => bot);
      })
      .then((bot) => {
        localStorage.removeItem(NEW_BOT_DRAFT_KEY);
        setHasDraft(false);
        return fetchBots().then(() => {
          setSelectedBot(bot.username);
        });
      })
      .then(() => {
        toast({
          title: t("botSettings.created"),
          status: "success",
          duration: 2500,
          isClosable: true,
          position: "top",
        });
      })
      .finally(() => setCreating(false));
  };

  const deleteBot = () => {
    if (!selectedBot) return;
    if (
      !window.confirm(
        t("botSettings.deleteConfirm", { username: `@${selectedBot}` })
      )
    ) {
      return;
    }

    setDeleting(true);
    const deletedKey = getDraftKey(selectedBot);
    fetch(`/bots/${selectedBot}`, { method: "DELETE" })
      .then(() => {
        localStorage.removeItem(deletedKey);
        setHasDraft(false);
        return fetchBots();
      })
      .then(() => {
        toast({
          title: t("botSettings.deleted"),
          status: "success",
          duration: 2500,
          isClosable: true,
          position: "top",
        });
      })
      .finally(() => setDeleting(false));
  };

  return (
    <Modal
      isOpen={isEditingBotSettings}
      onClose={close}
      size="4xl"
      scrollBehavior="inside"
    >
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent maxH="90vh" display="flex" flexDirection="column">
        <ModalHeader flexShrink={0}>{t("botSettings.title")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody
          flex="1"
          minH={0}
          style={{
            scrollbarGutter: "stable",
          }}
        >
          <Tabs variant="enclosed" colorScheme="primary">
            <TabList>
              <Tab>{t("botSettings.tabBotInfo")}</Tab>
              <Tab>{t("botSettings.tabSubscription")}</Tab>
              <Tab>{t("botSettings.tabMessages")}</Tab>
              <Tab>{t("botSettings.tabV2rayJson")}</Tab>
            </TabList>
            {hasDraft && (
              <HStack
                mt={2}
                p={3}
                borderRadius="md"
                bg="yellow.50"
                _dark={{ bg: "yellow.900" }}
                border="1px solid"
                borderColor="yellow.200"
                _dark-border={{ borderColor: "yellow.700" }}
                justify="space-between"
              >
                <ChakraText
                  fontSize="sm"
                  color="yellow.800"
                  _dark={{ color: "yellow.200" }}
                >
                  {t("botSettings.draftFound")}
                </ChakraText>
                <HStack>
                  <Button size="xs" colorScheme="yellow" onClick={restoreDraft}>
                    {t("botSettings.draftRestore")}
                  </Button>
                  <Button size="xs" variant="ghost" onClick={discardDraft}>
                    {t("botSettings.draftDiscard")}
                  </Button>
                </HStack>
              </HStack>
            )}
            <TabPanels minH="400px" pt={2}>
              {/* Вкладка 1: Bot Info */}
              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <FormControl position="relative" ref={botSelectorRef}>
                    <FormLabel>{t("botSettings.bot")}</FormLabel>
                    <Input
                      placeholder={t("botSettings.botSearchPlaceholder")}
                      value={botSearch}
                      onChange={(e) => {
                        setBotSearch(e.target.value);
                        setIsBotListOpen(true);
                      }}
                      onFocus={() => setIsBotListOpen(true)}
                    />

                    {isBotListOpen && (
                      <Box
                        position="absolute"
                        top="70px"
                        left={0}
                        right={0}
                        zIndex={1000}
                        bg="chakra-body-bg"
                        border="1px solid"
                        borderColor="inherit"
                        borderRadius="md"
                        boxShadow="lg"
                        maxH="240px"
                        overflowY="auto"
                      >
                        <Box
                          px={3}
                          py={2}
                          cursor="pointer"
                          color="gray.500"
                          _hover={{
                            bg: "gray.50",
                            _dark: { bg: "gray.700" },
                          }}
                          onClick={() => {
                            setSelectedBot("");
                            setBotSearch("");
                            setIsBotListOpen(false);
                          }}
                        >
                          {t("botSettings.emptySelection")}
                        </Box>

                        {bots
                          .filter((bot) => {
                            const q = botSearch.toLowerCase().replace(/^@/, "");

                            if (!q) return true;

                            return (
                              bot.username.toLowerCase().includes(q) ||
                              (bot.title || "").toLowerCase().includes(q)
                            );
                          })
                          .map((bot) => (
                            <Box
                              key={bot.id}
                              px={3}
                              py={2}
                              cursor="pointer"
                              bg={
                                selectedBot === bot.username
                                  ? "primary.50"
                                  : undefined
                              }
                              _dark={{
                                bg:
                                  selectedBot === bot.username
                                    ? "primary.900"
                                    : undefined,
                              }}
                              _hover={{
                                bg: "gray.50",
                                _dark: { bg: "gray.700" },
                              }}
                              onClick={() => {
                                setSelectedBot(bot.username);
                                setBotSearch(`@${bot.username}`);
                                setIsBotListOpen(false);
                              }}
                            >
                              <strong>@{bot.username}</strong>

                              {bot.title && (
                                <ChakraText as="span" color="gray.500" ml={1}>
                                  — {bot.title}
                                </ChakraText>
                              )}
                            </Box>
                          ))}
                      </Box>
                    )}

                    <FormHelperText>{t("botSettings.botHint")}</FormHelperText>
                  </FormControl>

                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.newBotUsername")}</FormLabel>
                      <Input
                        value={botUsername}
                        onChange={(e) => {
                          setBotUsername(e.target.value);
                          saveDraft(settings, e.target.value, botTitle);
                        }}
                        placeholder="@my_vpn_bot"
                      />
                      <FormHelperText>
                        {t("botSettings.newBotUsernameHint")}
                      </FormHelperText>
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("botSettings.newBotTitle")}</FormLabel>
                      <Input
                        value={botTitle}
                        onChange={(e) => {
                          setBotTitle(e.target.value);
                          saveDraft(settings, botUsername, e.target.value);
                        }}
                        placeholder="My VPN Bot"
                      />
                      <FormHelperText>
                        {t("botSettings.newBotTitleHint")}
                      </FormHelperText>
                    </FormControl>
                  </HStack>

                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.botUrl")}</FormLabel>
                      <Input
                        value={settings.bot_url}
                        placeholder="https://t.me/my_vpn_bot"
                        onChange={(e) =>
                          updateSettings({ bot_url: e.target.value })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.botUrlHint")}
                      </FormHelperText>
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("botSettings.webUrl")}</FormLabel>
                      <Input
                        value={settings.web_url}
                        placeholder="https://cabinet.example.com"
                        onChange={(e) =>
                          updateSettings({ web_url: e.target.value })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.webUrlHint")}
                      </FormHelperText>
                    </FormControl>
                  </HStack>
                </VStack>
              </TabPanel>

              {/* Вкладка 2: Subscription Settings */}
              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.subSupportUrl")}</FormLabel>
                      <Input
                        value={settings.sub_support_url}
                        placeholder="https://t.me/support"
                        onChange={(e) =>
                          updateSettings({ sub_support_url: e.target.value })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.subSupportUrlHint")}
                      </FormHelperText>
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("botSettings.subProfileTitle")}</FormLabel>
                      <Input
                        value={settings.sub_profile_title}
                        placeholder="My VPN"
                        onChange={(e) =>
                          updateSettings({ sub_profile_title: e.target.value })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.subProfileTitleHint")}
                      </FormHelperText>
                    </FormControl>
                  </HStack>

                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.subProfileUrl")}</FormLabel>
                      <Input
                        value={settings.sub_profile_url}
                        placeholder="https://example.com/profile"
                        onChange={(e) =>
                          updateSettings({ sub_profile_url: e.target.value })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.subProfileUrlHint")}
                      </FormHelperText>
                    </FormControl>
                    <FormControl>
                      <FormLabel>
                        {t("botSettings.subUpdateInterval")}
                      </FormLabel>
                      <Input
                        value={settings.sub_update_interval}
                        onChange={(e) =>
                          updateSettings({
                            sub_update_interval: e.target.value,
                          })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.subUpdateIntervalHint")}
                      </FormHelperText>
                    </FormControl>
                  </HStack>

                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.subRoutingHapp")}</FormLabel>
                      <Input
                        value={settings.sub_routing_happ}
                        placeholder="happ://"
                        onChange={(e) =>
                          updateSettings({ sub_routing_happ: e.target.value })
                        }
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel>
                        {t("botSettings.subRoutingV2raytun")}
                      </FormLabel>
                      <Input
                        value={settings.sub_routing_v2raytun}
                        placeholder="v2ray://"
                        onChange={(e) =>
                          updateSettings({
                            sub_routing_v2raytun: e.target.value,
                          })
                        }
                      />
                    </FormControl>
                  </HStack>

                  <FormControl>
                    <FormLabel>{t("botSettings.subClientNote")}</FormLabel>
                    <Textarea
                      value={settings.sub_client_note}
                      placeholder="Текст, который увидит пользователь на странице подписки"
                      onChange={(e) =>
                        updateSettings({ sub_client_note: e.target.value })
                      }
                    />
                  </FormControl>
                  <HStack align="start">
                    <FormControl>
                      <FormLabel>{t("botSettings.bsDailyLimitGb")}</FormLabel>
                      <Input
                        type="number"
                        value={settings.bs_daily_limit ? String(settings.bs_daily_limit / GB_IN_BYTES) : ""}
                        placeholder="0"
                        onChange={(e) => {
                          const gb = parseFloat(e.target.value);
                          updateSettings({
                            bs_daily_limit: e.target.value === "" || isNaN(gb)
                              ? 0 : Math.round(gb * GB_IN_BYTES),
                          });
                        }}
                      />
                      <FormHelperText>{t("botSettings.bsDailyLimitGbHint")}</FormHelperText>
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("botSettings.bsMonthlyLimitGb")}</FormLabel>
                      <Input
                        type="number"
                        value={settings.bs_monthly_limit ? String(settings.bs_monthly_limit / GB_IN_BYTES) : ""}
                        placeholder="0"
                        onChange={(e) => {
                          const gb = parseFloat(e.target.value);
                          updateSettings({
                            bs_monthly_limit: e.target.value === "" || isNaN(gb)
                              ? 0 : Math.round(gb * GB_IN_BYTES),
                          });
                        }}
                      />
                      <FormHelperText>{t("botSettings.bsMonthlyLimitGbHint")}</FormHelperText>
                    </FormControl>
                  </HStack>
                </VStack>
              </TabPanel>

              {/* Вкладка 3: Messages */}
              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <Box
                    border="1px solid"
                    borderColor="inherit"
                    borderRadius="md"
                    p={4}
                  >
                    <VStack spacing={4} align="stretch">
                      <ChakraText
                        fontSize="xs"
                        fontWeight="semibold"
                        color="gray.500"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        {t("botSettings.announceMessages")}
                      </ChakraText>

                      <HStack align="start">
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subRevokedAnnounceText")}
                          </FormLabel>
                          <Input
                            value={settings.sub_revoked_announce_text}
                            placeholder="Подписка была отозвана"
                            onChange={(e) =>
                              updateSettings({
                                sub_revoked_announce_text: e.target.value,
                              })
                            }
                          />
                        </FormControl>
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subExpiredAnnounceText")}
                          </FormLabel>
                          <Input
                            value={settings.sub_expired_announce_text}
                            placeholder="Срок действия подписки истёк"
                            onChange={(e) =>
                              updateSettings({
                                sub_expired_announce_text: e.target.value,
                              })
                            }
                          />
                        </FormControl>
                      </HStack>

                      <HStack align="start">
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subUnsupportedClientAnnounceText")}
                          </FormLabel>
                          <Input
                            value={
                              settings.sub_unsupported_client_announce_text
                            }
                            placeholder="Ваш клиент не поддерживается"
                            onChange={(e) =>
                              updateSettings({
                                sub_unsupported_client_announce_text:
                                  e.target.value,
                              })
                            }
                          />
                        </FormControl>
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subDeviceLimitAnnounceText")}
                          </FormLabel>
                          <Input
                            value={settings.sub_device_limit_announce_text}
                            placeholder="Превышен лимит устройств"
                            onChange={(e) =>
                              updateSettings({
                                sub_device_limit_announce_text: e.target.value,
                              })
                            }
                          />
                        </FormControl>
                      </HStack>
                    </VStack>
                  </Box>

                  <Box
                    border="1px solid"
                    borderColor="inherit"
                    borderRadius="md"
                    p={4}
                  >
                    <FormControl>
                      <FormLabel>
                        {t("botSettings.subDeviceLimitHardMode")}
                      </FormLabel>
                      <Switch
                        colorScheme="primary"
                        isChecked={settings.sub_device_limit_hard_mode}
                        onChange={(e) =>
                          updateSettings({
                            sub_device_limit_hard_mode: e.target.checked,
                          })
                        }
                      />
                      <FormHelperText>
                        {t("botSettings.subDeviceLimitHardModeHint")}
                      </FormHelperText>
                    </FormControl>
                  </Box>

                  {/* Server Responses */}
                  <Box
                    border="1px solid"
                    borderColor="inherit"
                    borderRadius="md"
                    p={4}
                  >
                    <VStack spacing={4} align="stretch">
                      <ChakraText
                        fontSize="xs"
                        fontWeight="semibold"
                        color="gray.500"
                        textTransform="uppercase"
                        letterSpacing="wide"
                      >
                        {t("botSettings.serverResponses")}
                      </ChakraText>

                      <HStack align="start">
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subRevokedServerText")}
                          </FormLabel>
                          <Textarea
                            value={listFieldTexts.sub_revoked_server_text}
                            onChange={(e) =>
                              updateListField(
                                "sub_revoked_server_text",
                                e.target.value
                              )
                            }
                          />
                          <FormHelperText>
                            {t("botSettings.serverTextHint")}
                          </FormHelperText>
                        </FormControl>
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subExpiredServerText")}
                          </FormLabel>
                          <Textarea
                            value={listFieldTexts.sub_expired_server_text}
                            onChange={(e) =>
                              updateListField(
                                "sub_expired_server_text",
                                e.target.value
                              )
                            }
                          />
                          <FormHelperText>
                            {t("botSettings.serverTextHint")}
                          </FormHelperText>
                        </FormControl>
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subBsLimitServerText")}
                          </FormLabel>
                          <Textarea
                            value={listFieldTexts.sub_bs_limit_server_text}
                            onChange={(e) =>
                              updateListField(
                                "sub_bs_limit_server_text",
                                e.target.value
                              )
                            }
                          />
                          <FormHelperText>
                            {t("botSettings.serverTextHint")}
                          </FormHelperText>
                        </FormControl>
                      </HStack>
                      <HStack align="start">
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subBsLimitAnnounceText")}
                          </FormLabel>
                          <Input
                            value={settings.sub_bs_limit_announce_text}
                            onChange={(e) =>
                              updateSettings({
                                sub_bs_limit_announce_text: e.target.value,
                              })
                            }
                          />
                        </FormControl>
                      </HStack>
                      <HStack align="start">
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subDeviceLimitServerText")}
                          </FormLabel>
                          <Textarea
                            value={listFieldTexts.sub_device_limit_server_text}
                            onChange={(e) =>
                              updateListField(
                                "sub_device_limit_server_text",
                                e.target.value
                              )
                            }
                          />
                          <FormHelperText>
                            {t("botSettings.serverTextHint")}
                          </FormHelperText>
                        </FormControl>
                        <FormControl>
                          <FormLabel>
                            {t("botSettings.subUnsupportedClientServerText")}
                          </FormLabel>
                          <Textarea
                            value={
                              listFieldTexts.sub_unsupported_client_server_text
                            }
                            onChange={(e) =>
                              updateListField(
                                "sub_unsupported_client_server_text",
                                e.target.value
                              )
                            }
                          />
                          <FormHelperText>
                            {t("botSettings.serverTextHint")}
                          </FormHelperText>
                        </FormControl>
                      </HStack>
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>

              {/* Вкладка 4: v2ray-json */}
              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <FormControl>
                    <FormLabel>{t("botSettings.v2rayJsonTemplate")}</FormLabel>
                    <Textarea
                      fontFamily="mono"
                      minH="180px"
                      value={settings.sub_v2ray_json_template}
                      placeholder='{ "dns": {...}, "routing": {...}, ... }'
                      onChange={(e) =>
                        updateSettings({
                          sub_v2ray_json_template: e.target.value,
                        })
                      }
                    />
                    <FormHelperText>
                      {t("botSettings.v2rayJsonTemplateHint")}
                    </FormHelperText>
                  </FormControl>
                  <FormControl>
                    <FormLabel>{t("botSettings.routingDefault")}</FormLabel>
                    <Textarea
                      fontFamily="mono"
                      minH="140px"
                      value={settings.sub_routing_json_default}
                      placeholder='{ "domainStrategy": "IPIfNonMatch", "rules": [...] }'
                      onChange={(e) =>
                        updateSettings({
                          sub_routing_json_default: e.target.value,
                        })
                      }
                    />
                    <FormHelperText>
                      {t("botSettings.routingDefaultHint")}
                    </FormHelperText>
                  </FormControl>
                  <FormControl>
                    <FormLabel>{t("botSettings.routingBs")}</FormLabel>
                    <Textarea
                      fontFamily="mono"
                      minH="140px"
                      value={settings.sub_routing_json_bs}
                      placeholder='{ "domainStrategy": "AsIs", "rules": [...] }'
                      onChange={(e) =>
                        updateSettings({ sub_routing_json_bs: e.target.value })
                      }
                    />
                    <FormHelperText>
                      {t("botSettings.routingBsHint")}
                    </FormHelperText>
                  </FormControl>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
        <ModalFooter>
          <HStack justifyContent="space-between" width="full">
            <HStack>
              <Button
                variant="outline"
                colorScheme="green"
                onClick={createBot}
                isLoading={creating}
                isDisabled={!!selectedBot || !botUsername.trim()}
              >
                {t("botSettings.createBot")}
              </Button>
              <Button
                variant="outline"
                colorScheme="red"
                onClick={deleteBot}
                isLoading={deleting}
                isDisabled={!selectedBot}
              >
                {t("botSettings.deleteBot")}
              </Button>
            </HStack>
            <HStack>
              <Button variant="ghost" mr={3} onClick={close}>
                {t("cancel")}
              </Button>
              <Button
                colorScheme="primary"
                onClick={save}
                isLoading={saving}
                isDisabled={loading || !selectedBot || !botUsername.trim()}
              >
                {t("core.save")}
              </Button>
            </HStack>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
