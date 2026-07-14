import {
  Button,
  Checkbox,
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
  SimpleGrid,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";
import {
  ClientApp,
  ClientAppsSettings,
  LINK_KEYS,
  PLATFORM_KEYS,
  PlatformKey,
} from "types/AppSettings";

// Локальный тип для рендера: добавляем стабильный технический ключ, который
// не отправляется на бэкенд (см. toPayload), чтобы React не переиспользовал
// инпуты между позициями при перемещении/удалении карточек.
type ClientAppWithKey = ClientApp & { _key: number };

type ClientAppsSettingsWithKeys = {
  apps: ClientAppWithKey[];
  primary_by_platform: ClientAppsSettings["primary_by_platform"];
};

const emptyLinks = () =>
  LINK_KEYS.reduce(
    (acc, key) => ({ ...acc, [key]: "" }),
    {} as ClientApp["links"]
  );

const emptySettings: ClientAppsSettingsWithKeys = { apps: [], primary_by_platform: {} };

const newApp = (index: number): ClientApp => ({
  id: `app${index}`,
  name: "",
  scheme: "",
  enabled: true,
  links: emptyLinks(),
});

const toPayload = (settings: ClientAppsSettingsWithKeys): ClientAppsSettings => ({
  ...settings,
  apps: settings.apps.map(({ _key, ...app }) => app),
});

export const AppSettingsDialog: FC = () => {
  const { isEditingAppSettings, onEditingAppSettings } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();
  const [settings, setSettings] = useState<ClientAppsSettingsWithKeys>(emptySettings);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const nextKeyRef = useRef(0);
  const withKeys = (data: ClientAppsSettings): ClientAppsSettingsWithKeys => ({
    ...data,
    apps: data.apps.map((app) => ({ ...app, _key: nextKeyRef.current++ })),
  });

  const showValidationErrorToast = (err: any) => {
    const detail = err?.response?._data?.detail;
    if (detail && typeof detail === "object") {
      Object.keys(detail).forEach((key) => {
        toast({
          title: `${detail[key]} (${key})`,
          status: "error",
          isClosable: true,
          position: "top",
        });
      });
      return;
    }
    toast({
      title: t("appSettings.saveFailed"),
      description: typeof detail === "string" ? detail : undefined,
      status: "error",
      isClosable: true,
      position: "top",
    });
  };

  useEffect(() => {
    if (!isEditingAppSettings) return;
    setSettings(emptySettings);
    setLoading(true);
    fetch("/settings/apps")
      .then((data: ClientAppsSettings) => setSettings(withKeys(data)))
      .catch(() =>
        toast({
          title: t("appSettings.loadFailed"),
          status: "error",
          isClosable: true,
          position: "top",
        })
      )
      .finally(() => setLoading(false));
  }, [isEditingAppSettings]);

  const updateApp = (index: number, patch: Partial<ClientApp>) => {
    setSettings((prev) => {
      const target = prev.apps[index];
      const apps = prev.apps.map((app, i) => (i === index ? { ...app, ...patch } : app));
      // При переименовании id переносим ссылки primary_by_platform, указывавшие
      // на старый id, на новый — иначе они "теряются" и сохранение падает с 422.
      if (patch.id !== undefined && target && patch.id !== target.id) {
        const oldId = target.id;
        const newId = patch.id;
        const primary = { ...prev.primary_by_platform };
        PLATFORM_KEYS.forEach((platform) => {
          if (primary[platform] === oldId) primary[platform] = newId;
        });
        return { apps, primary_by_platform: primary };
      }
      return { ...prev, apps };
    });
  };

  const updateLink = (index: number, key: string, value: string) => {
    setSettings((prev) => ({
      ...prev,
      apps: prev.apps.map((app, i) =>
        i === index ? { ...app, links: { ...app.links, [key]: value } } : app
      ),
    }));
  };

  const moveApp = (index: number, delta: number) => {
    setSettings((prev) => {
      const apps = [...prev.apps];
      const target = index + delta;
      if (target < 0 || target >= apps.length) return prev;
      [apps[index], apps[target]] = [apps[target], apps[index]];
      return { ...prev, apps };
    });
  };

  const removeApp = (index: number) => {
    setSettings((prev) => {
      const removed = prev.apps[index];
      const primary = { ...prev.primary_by_platform };
      PLATFORM_KEYS.forEach((platform) => {
        if (primary[platform] === removed.id) delete primary[platform];
      });
      return {
        apps: prev.apps.filter((_, i) => i !== index),
        primary_by_platform: primary,
      };
    });
  };

  const resetToDefaults = () => {
    setLoading(true);
    fetch("/settings/apps/defaults")
      .then((data: ClientAppsSettings) => setSettings(withKeys(data)))
      .catch(() =>
        toast({
          title: t("appSettings.loadFailed"),
          status: "error",
          isClosable: true,
          position: "top",
        })
      )
      .finally(() => setLoading(false));
  };

  const save = () => {
    setSaving(true);
    fetch("/settings/apps", { method: "PUT", body: toPayload(settings) })
      .then((data: ClientAppsSettings) => {
        setSettings(withKeys(data));
        toast({
          title: t("appSettings.saved"),
          status: "success",
          isClosable: true,
          position: "top",
        });
        onEditingAppSettings(false);
      })
      .catch((err) => showValidationErrorToast(err))
      .finally(() => setSaving(false));
  };

  return (
    <Modal
      isOpen={isEditingAppSettings}
      onClose={() => onEditingAppSettings(false)}
      size="4xl"
      scrollBehavior="inside"
    >
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{t("appSettings.title")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing={6}>
            <VStack align="stretch" spacing={4}>
              {settings.apps.map((app, index) => (
                <VStack
                  key={app._key}
                  align="stretch"
                  spacing={3}
                  borderWidth="1px"
                  borderRadius="md"
                  p={4}
                >
                  <HStack justify="space-between" align="start" spacing={3}>
                    <HStack spacing={3} flexWrap="wrap" align="end" flex="1" minW={0}>
                      <FormControl flex="1 1 140px" minW="120px" maxW="180px">
                        <FormLabel fontSize="sm">{t("appSettings.appId")}</FormLabel>
                        <Input
                          placeholder="happ"
                          value={app.id}
                          onChange={(e) => updateApp(index, { id: e.target.value })}
                        />
                      </FormControl>
                      <FormControl flex="1 1 200px" minW="140px" maxW="240px">
                        <FormLabel fontSize="sm">{t("appSettings.appName")}</FormLabel>
                        <Input
                          placeholder="Happ"
                          value={app.name}
                          onChange={(e) => updateApp(index, { name: e.target.value })}
                        />
                      </FormControl>
                      <FormControl flex="1 1 140px" minW="120px" maxW="180px">
                        <FormLabel fontSize="sm">{t("appSettings.scheme")}</FormLabel>
                        <Input
                          placeholder="happ"
                          value={app.scheme}
                          onChange={(e) => updateApp(index, { scheme: e.target.value })}
                        />
                      </FormControl>
                      <Checkbox
                        flexShrink={0}
                        pb={2}
                        isChecked={app.enabled}
                        onChange={(e) => updateApp(index, { enabled: e.target.checked })}
                      >
                        {t("appSettings.enabled")}
                      </Checkbox>
                    </HStack>
                    <HStack flexShrink={0} pt={8}>
                      <Button size="sm" onClick={() => moveApp(index, -1)}>↑</Button>
                      <Button size="sm" onClick={() => moveApp(index, 1)}>↓</Button>
                      <Button
                        size="sm"
                        colorScheme="red"
                        whiteSpace="nowrap"
                        onClick={() => removeApp(index)}
                      >
                        {t("delete")}
                      </Button>
                    </HStack>
                  </HStack>
                  <SimpleGrid columns={2} spacing={3}>
                    {LINK_KEYS.map((key) => (
                      <FormControl key={key}>
                        <FormLabel fontSize="sm">{t(`appSettings.link.${key}`)}</FormLabel>
                        <Input
                          size="sm"
                          placeholder="https://…"
                          value={app.links[key] ?? ""}
                          onChange={(e) => updateLink(index, key, e.target.value)}
                        />
                      </FormControl>
                    ))}
                  </SimpleGrid>
                </VStack>
              ))}
              <Button
                alignSelf="flex-start"
                size="sm"
                onClick={() =>
                  setSettings((prev) => ({
                    ...prev,
                    apps: [
                      ...prev.apps,
                      { ...newApp(prev.apps.length + 1), _key: nextKeyRef.current++ },
                    ],
                  }))
                }
              >
                {t("appSettings.addApp")}
              </Button>
            </VStack>

            <VStack align="stretch" spacing={3}>
              <Text fontWeight="semibold">{t("appSettings.primaryByPlatform")}</Text>
              <SimpleGrid columns={3} spacing={3}>
                {PLATFORM_KEYS.map((platform: PlatformKey) => (
                  <FormControl key={platform}>
                    <FormLabel fontSize="sm">{t(`appSettings.platform.${platform}`)}</FormLabel>
                    <Select
                      size="sm"
                      value={settings.primary_by_platform[platform] ?? ""}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          primary_by_platform: {
                            ...prev.primary_by_platform,
                            [platform]: e.target.value,
                          },
                        }))
                      }
                    >
                      <option value="">—</option>
                      {settings.apps
                        .filter((app) => app.enabled)
                        .map((app) => (
                          <option key={app.id} value={app.id}>
                            {app.name || app.id}
                          </option>
                        ))}
                    </Select>
                  </FormControl>
                ))}
              </SimpleGrid>
            </VStack>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack>
            <Button variant="outline" onClick={resetToDefaults} isLoading={loading}>
              {t("appSettings.resetDefaults")}
            </Button>
            <Button colorScheme="primary" onClick={save} isLoading={saving}>
              {t("core.save")}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
