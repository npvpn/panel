import {
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
  Select,
  Textarea,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { FC, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDashboard } from "contexts/DashboardContext";
import { fetch } from "service/http";
import { Bot, BotSettings } from "types/Bot";

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
  sub_revoked_announce_text: "",
  sub_expired_announce_text: "",
  sub_device_limit_announce_text: "",
  sub_unsupported_client_announce_text: "",
  sub_revoked_server_text: [],
  sub_expired_server_text: [],
  sub_device_limit_server_text: [],
  sub_unsupported_client_server_text: [],
};

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
  const [defaultSettings, setDefaultSettings] = useState<BotSettings>(emptySettings);
  const [botUsername, setBotUsername] = useState("");
  const [botTitle, setBotTitle] = useState("");
  const [settings, setSettings] = useState<BotSettings>(emptySettings);

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
    if (!isEditingBotSettings) return;
    setLoading(true);
    setSelectedBot("");
    setBotUsername("");
    setBotTitle("");
    setSettings(emptySettings);
    Promise.all([fetchBots(), fetch<BotSettings>("/bots/default-settings").then(setDefaultSettings)])
      .finally(() => setLoading(false));
  }, [isEditingBotSettings]);

  useEffect(() => {
    if (!isEditingBotSettings) return;
    if (!selectedBot) {
      setBotUsername("");
      setBotTitle("");
      setSettings(emptySettings);
      return;
    }
    const selected = bots.find((bot) => bot.username === selectedBot);
    setBotUsername(selected?.username || "");
    setBotTitle(selected?.title || "");
    setLoading(true);
    fetch<BotSettings>(`/bots/${selectedBot}/settings`)
      .then(setSettings)
      .finally(() => setLoading(false));
  }, [isEditingBotSettings, selectedBot, bots]);

  const close = () => onEditingBotSettings(false);

  const listFields = useMemo(
    () => ({
      sub_revoked_server_text: toText(settings.sub_revoked_server_text),
      sub_expired_server_text: toText(settings.sub_expired_server_text),
      sub_device_limit_server_text: toText(settings.sub_device_limit_server_text),
      sub_unsupported_client_server_text: toText(settings.sub_unsupported_client_server_text),
    }),
    [settings]
  );
  const selectedBotModel = useMemo(
    () => bots.find((bot) => bot.username === selectedBot),
    [bots, selectedBot]
  );

  const mergeWithDefaults = (current: BotSettings): BotSettings => {
    return {
      sub_update_interval: current.sub_update_interval.trim() || defaultSettings.sub_update_interval,
      sub_support_url: current.sub_support_url.trim() || defaultSettings.sub_support_url,
      sub_profile_title: current.sub_profile_title.trim() || defaultSettings.sub_profile_title,
      sub_routing_happ: current.sub_routing_happ.trim() || defaultSettings.sub_routing_happ,
      sub_routing_v2raytun: current.sub_routing_v2raytun.trim() || defaultSettings.sub_routing_v2raytun,
      sub_client_note: current.sub_client_note.trim() || defaultSettings.sub_client_note,
      sub_profile_url: current.sub_profile_url.trim() || defaultSettings.sub_profile_url,
      bot_url: current.bot_url.trim() || defaultSettings.bot_url,
      sub_revoked_announce_text:
        current.sub_revoked_announce_text.trim() || defaultSettings.sub_revoked_announce_text,
      sub_expired_announce_text:
        current.sub_expired_announce_text.trim() || defaultSettings.sub_expired_announce_text,
      sub_device_limit_announce_text:
        current.sub_device_limit_announce_text.trim() || defaultSettings.sub_device_limit_announce_text,
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
      sub_revoked_server_text: toList(listFields.sub_revoked_server_text),
      sub_expired_server_text: toList(listFields.sub_expired_server_text),
      sub_device_limit_server_text: toList(listFields.sub_device_limit_server_text),
      sub_unsupported_client_server_text: toList(
        listFields.sub_unsupported_client_server_text
      ),
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
        setSettings(updated);
        return fetchBots().then(() => {
          setSelectedBot(targetUsername);
        });
      })
      .then(() => {
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
    if (!window.confirm(t("botSettings.deleteConfirm", { username: `@${selectedBot}` }))) {
      return;
    }

    setDeleting(true);
    fetch(`/bots/${selectedBot}`, { method: "DELETE" })
      .then(() => fetchBots())
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
    <Modal isOpen={isEditingBotSettings} onClose={close} size="4xl">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent>
        <ModalHeader>{t("botSettings.title")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={3} align="stretch">
            <FormControl>
              <FormLabel>{t("botSettings.bot")}</FormLabel>
              <Select
                value={selectedBot}
                onChange={(event) => setSelectedBot(event.target.value)}
                isDisabled={loading}
              >
                <option value="">{t("botSettings.emptySelection")}</option>
                {bots.map((bot) => (
                  <option key={bot.id} value={bot.username}>
                    @{bot.username}
                    {bot.title ? ` - ${bot.title}` : ""}
                  </option>
                ))}
              </Select>
              <FormHelperText>{t("botSettings.botHint")}</FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>{t("botSettings.newBotUsername")}</FormLabel>
              <Input
                value={botUsername}
                onChange={(event) => setBotUsername(event.target.value)}
                placeholder="@my_vpn_bot"
              />
              <FormHelperText>{t("botSettings.newBotUsernameHint")}</FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>{t("botSettings.newBotTitle")}</FormLabel>
              <Input
                value={botTitle}
                onChange={(event) => setBotTitle(event.target.value)}
                placeholder="My VPN Bot"
              />
              <FormHelperText>{t("botSettings.newBotTitleHint")}</FormHelperText>
            </FormControl>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subSupportUrl")}</FormLabel>
                <Input
                  value={settings.sub_support_url}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_support_url: event.target.value,
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.subSupportUrlHint")}</FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subProfileTitle")}</FormLabel>
                <Input
                  value={settings.sub_profile_title}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_profile_title: event.target.value,
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.subProfileTitleHint")}</FormHelperText>
              </FormControl>
            </HStack>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.botUrl")}</FormLabel>
                <Input
                  value={settings.bot_url}
                  onChange={(event) =>
                    setSettings((prev) => ({ ...prev, bot_url: event.target.value }))
                  }
                />
                <FormHelperText>{t("botSettings.botUrlHint")}</FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subProfileUrl")}</FormLabel>
                <Input
                  value={settings.sub_profile_url}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_profile_url: event.target.value,
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.subProfileUrlHint")}</FormHelperText>
              </FormControl>
            </HStack>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subRoutingHapp")}</FormLabel>
                <Input
                  value={settings.sub_routing_happ}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_routing_happ: event.target.value,
                    }))
                  }
                />
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subRoutingV2raytun")}</FormLabel>
                <Input
                  value={settings.sub_routing_v2raytun}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_routing_v2raytun: event.target.value,
                    }))
                  }
                />
              </FormControl>
            </HStack>

            <FormControl>
              <FormLabel>{t("botSettings.subClientNote")}</FormLabel>
              <Textarea
                value={settings.sub_client_note}
                onChange={(event) =>
                  setSettings((prev) => ({ ...prev, sub_client_note: event.target.value }))
                }
              />
            </FormControl>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subRevokedAnnounceText")}</FormLabel>
                <Input
                  value={settings.sub_revoked_announce_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_revoked_announce_text: event.target.value,
                    }))
                  }
                />
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subExpiredAnnounceText")}</FormLabel>
                <Input
                  value={settings.sub_expired_announce_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_expired_announce_text: event.target.value,
                    }))
                  }
                />
              </FormControl>
            </HStack>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subDeviceLimitAnnounceText")}</FormLabel>
                <Input
                  value={settings.sub_device_limit_announce_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_device_limit_announce_text: event.target.value,
                    }))
                  }
                />
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subUnsupportedClientAnnounceText")}</FormLabel>
                <Input
                  value={settings.sub_unsupported_client_announce_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_unsupported_client_announce_text: event.target.value,
                    }))
                  }
                />
              </FormControl>
            </HStack>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subRevokedServerText")}</FormLabel>
                <Textarea
                  value={listFields.sub_revoked_server_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_revoked_server_text: toList(event.target.value),
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.serverTextHint")}</FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subExpiredServerText")}</FormLabel>
                <Textarea
                  value={listFields.sub_expired_server_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_expired_server_text: toList(event.target.value),
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.serverTextHint")}</FormHelperText>
              </FormControl>
            </HStack>

            <HStack>
              <FormControl>
                <FormLabel>{t("botSettings.subDeviceLimitServerText")}</FormLabel>
                <Textarea
                  value={listFields.sub_device_limit_server_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_device_limit_server_text: toList(event.target.value),
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.serverTextHint")}</FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>{t("botSettings.subUnsupportedClientServerText")}</FormLabel>
                <Textarea
                  value={listFields.sub_unsupported_client_server_text}
                  onChange={(event) =>
                    setSettings((prev) => ({
                      ...prev,
                      sub_unsupported_client_server_text: toList(event.target.value),
                    }))
                  }
                />
                <FormHelperText>{t("botSettings.serverTextHint")}</FormHelperText>
              </FormControl>
            </HStack>

            <FormControl>
              <FormLabel>{t("botSettings.subUpdateInterval")}</FormLabel>
              <Input
                value={settings.sub_update_interval}
                onChange={(event) =>
                  setSettings((prev) => ({
                    ...prev,
                    sub_update_interval: event.target.value,
                  }))
                }
              />
              <FormHelperText>{t("botSettings.subUpdateIntervalHint")}</FormHelperText>
            </FormControl>
          </VStack>
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
