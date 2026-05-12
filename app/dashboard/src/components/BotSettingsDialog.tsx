import {
  Button,
  FormControl,
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
  const [settings, setSettings] = useState<BotSettings>(emptySettings);

  useEffect(() => {
    if (!isEditingBotSettings) return;
    setLoading(true);
    fetch<Bot[]>("/bots")
      .then((items) => {
        setBots(items);
        if (items.length > 0) {
          setSelectedBot((prev) => prev || items[0].username);
        }
      })
      .catch(() => {
        setBots([]);
      })
      .finally(() => setLoading(false));
  }, [isEditingBotSettings]);

  useEffect(() => {
    if (!isEditingBotSettings || !selectedBot) return;
    setLoading(true);
    fetch<BotSettings>(`/bots/${selectedBot}/settings`)
      .then(setSettings)
      .finally(() => setLoading(false));
  }, [isEditingBotSettings, selectedBot]);

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

  const save = () => {
    if (!selectedBot) return;
    setSaving(true);
    fetch<BotSettings>(`/bots/${selectedBot}/settings`, {
      method: "PUT",
      body: {
        ...settings,
        sub_revoked_server_text: toList(listFields.sub_revoked_server_text),
        sub_expired_server_text: toList(listFields.sub_expired_server_text),
        sub_device_limit_server_text: toList(listFields.sub_device_limit_server_text),
        sub_unsupported_client_server_text: toList(
          listFields.sub_unsupported_client_server_text
        ),
      },
    })
      .then((updated) => {
        setSettings(updated);
        toast({
          title: t("botSettings.saved"),
          status: "success",
          duration: 2500,
          isClosable: true,
          position: "top",
        });
      })
      .finally(() => setSaving(false));
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
                isDisabled={loading || bots.length === 0}
              >
                {bots.map((bot) => (
                  <option key={bot.id} value={bot.username}>
                    @{bot.username}
                  </option>
                ))}
              </Select>
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
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={close}>
            {t("cancel")}
          </Button>
          <Button
            colorScheme="primary"
            onClick={save}
            isLoading={saving}
            isDisabled={loading || !selectedBot}
          >
            {t("core.save")}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
