import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
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
  Tooltip,
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
import { DeleteIcon } from "./DeleteUserModal";

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

const emptySettings: ClientAppsSettingsWithKeys = {
  apps: [],
  primary_by_platform: {},
};

const newApp = (index: number): ClientApp => ({
  id: `app${index}`,
  name: "",
  scheme: "",
  enabled: true,
  links: emptyLinks(),
});

const toPayload = (
  settings: ClientAppsSettingsWithKeys
): ClientAppsSettings => ({
  ...settings,
  apps: settings.apps.map(({ _key, ...app }) => app),
});

const MoveUpIcon: FC = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path
      d="M6 10V2M6 2L2.5 5.5M6 2L9.5 5.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const MoveDownIcon: FC = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path
      d="M6 2V10M6 10L2.5 6.5M6 10L9.5 6.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const isAppIncomplete = (app: ClientApp) =>
  !app.id.trim() || !app.name.trim() || !app.scheme.trim();

const thinScrollbarSx = {
  "&::-webkit-scrollbar": {
    width: "6px",
  },
  "&::-webkit-scrollbar-track": {
    background: "transparent",
  },
  "&::-webkit-scrollbar-thumb": {
    background: "var(--chakra-colors-gray-300)",
    borderRadius: "full",
  },
  "&::-webkit-scrollbar-thumb:hover": {
    background: "var(--chakra-colors-gray-400)",
  },
  scrollbarWidth: "thin",
  scrollbarColor: "var(--chakra-colors-gray-300) transparent",
} as const;

export const AppSettingsDialog: FC = () => {
  const { isEditingAppSettings, onEditingAppSettings } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();
  const [settings, setSettings] =
    useState<ClientAppsSettingsWithKeys>(emptySettings);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [openIndexes, setOpenIndexes] = useState<number[]>([]);
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
    setOpenIndexes([]);
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
      const apps = prev.apps.map((app, i) =>
        i === index ? { ...app, ...patch } : app
      );

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

    setOpenIndexes((prev) =>
      prev.map((i) => {
        if (i === index) return index + delta;
        if (i === index + delta) return index;
        return i;
      })
    );
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
    setOpenIndexes((prev) =>
      prev.filter((i) => i !== index).map((i) => (i > index ? i - 1 : i))
    );
  };

  const resetToDefaults = () => {
    setLoading(true);
    fetch("/settings/apps/defaults")
      .then((data: ClientAppsSettings) => {
        setSettings(withKeys(data));
        setOpenIndexes([]);
      })
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

  const addApp = () => {
    setSettings((prev) => ({
      ...prev,
      apps: [
        ...prev.apps,
        { ...newApp(prev.apps.length + 1), _key: nextKeyRef.current++ },
      ],
    }));
    setOpenIndexes((prev) => [...prev, settings.apps.length]);
  };

  const save = () => {
    setSaving(true);
    fetch("/settings/apps", { method: "PUT", body: toPayload(settings) })
      .then((data: ClientAppsSettings) => {
        setSettings(withKeys(data));
        setOpenIndexes([]);
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
        <ModalBody sx={thinScrollbarSx}>
          <VStack align="stretch" spacing={6}>
            {/* Выбор приложений */}
            <VStack align="stretch" spacing={3}>
              <Text fontWeight="semibold">
                {t("appSettings.primaryByPlatform")}
              </Text>
              <SimpleGrid columns={{ base: 1, sm: 2, md: 3 }} spacing={3}>
                {PLATFORM_KEYS.map((platform: PlatformKey) => (
                  <FormControl key={platform}>
                    <FormLabel fontSize="sm">
                      {t(`appSettings.platform.${platform}`)}
                    </FormLabel>
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

            {/* Список приложений */}
            <VStack align="stretch" spacing={3}>
              <Text fontWeight="semibold">{t("appSettings.appsList")}</Text>

              {settings.apps.length === 0 ? (
                <Text fontSize="sm" color="gray.500">
                  {t("appSettings.noApps")}
                </Text>
              ) : (
                <Accordion
                  allowMultiple
                  index={openIndexes}
                  onChange={(indexes) => setOpenIndexes(indexes as number[])}
                >
                  {settings.apps.map((app, index) => (
                    <AccordionItem
                      key={app._key}
                      borderWidth="1px"
                      borderRadius="md"
                      mb={2}
                    >
                      <Box
                        _hover={{ bg: "gray.50" }}
                        borderRadius="md"
                        transition="background 0.15s"
                      >
                        <HStack spacing={0} align="center">
                          <AccordionButton
                            flex="1"
                            minW={0}
                            _hover={{ bg: "transparent" }}
                          >
                            <HStack
                              flex="1"
                              spacing={3}
                              minW={0}
                              textAlign="left"
                            >
                              <Checkbox
                                isChecked={app.enabled}
                                onChange={(e) =>
                                  updateApp(index, {
                                    enabled: e.target.checked,
                                  })
                                }
                                onClick={(e) => e.stopPropagation()}
                              />
                              <Box minW={0}>
                                <HStack spacing={2}>
                                  <Text fontWeight="medium" noOfLines={1}>
                                    {app.name ||
                                      app.id ||
                                      t("appSettings.appName")}
                                  </Text>
                                  {isAppIncomplete(app) && (
                                    <Tooltip
                                      label={t("appSettings.incomplete")}
                                      fontSize="xs"
                                      hasArrow
                                    >
                                      <Box
                                        w="6px"
                                        h="6px"
                                        borderRadius="full"
                                        bg="orange.400"
                                        flexShrink={0}
                                      />
                                    </Tooltip>
                                  )}
                                </HStack>
                                <Text
                                  fontSize="xs"
                                  color="gray.500"
                                  noOfLines={1}
                                >
                                  {app.id}
                                </Text>
                              </Box>
                            </HStack>
                            <AccordionIcon />
                          </AccordionButton>
                          <HStack flexShrink={0} px={2}>
                            <Tooltip
                              label={t("appSettings.moveUp")}
                              fontSize="xs"
                              hasArrow
                            >
                              <IconButton
                                aria-label={t("appSettings.moveUp")}
                                icon={<MoveUpIcon />}
                                size="sm"
                                variant="ghost"
                                isDisabled={index === 0}
                                onClick={() => moveApp(index, -1)}
                              />
                            </Tooltip>
                            <Tooltip
                              label={t("appSettings.moveDown")}
                              fontSize="xs"
                              hasArrow
                            >
                              <IconButton
                                aria-label={t("appSettings.moveDown")}
                                icon={<MoveDownIcon />}
                                size="sm"
                                variant="ghost"
                                isDisabled={index === settings.apps.length - 1}
                                onClick={() => moveApp(index, 1)}
                              />
                            </Tooltip>
                            <Tooltip label={t("delete")} fontSize="xs" hasArrow>
                              <IconButton
                                aria-label={t("delete")}
                                icon={<DeleteIcon />}
                                size="sm"
                                variant="ghost"
                                colorScheme="red"
                                onClick={() => removeApp(index)}
                              />
                            </Tooltip>
                          </HStack>
                        </HStack>
                      </Box>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={3}>
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            textTransform="uppercase"
                            fontWeight="semibold"
                            letterSpacing="wide"
                          >
                            {t("appSettings.general")}
                          </Text>
                          <HStack spacing={3} flexWrap="wrap" align="end">
                            <FormControl
                              flex="1 1 140px"
                              minW="120px"
                              isInvalid={!app.id.trim()}
                              isRequired
                            >
                              <FormLabel fontSize="sm">
                                {t("appSettings.appId")}
                              </FormLabel>
                              <Input
                                placeholder="happ"
                                value={app.id}
                                onChange={(e) =>
                                  updateApp(index, { id: e.target.value })
                                }
                              />
                            </FormControl>
                            <FormControl
                              flex="1 1 200px"
                              minW="140px"
                              isInvalid={!app.name.trim()}
                              isRequired
                            >
                              <FormLabel fontSize="sm">
                                {t("appSettings.appName")}
                              </FormLabel>
                              <Input
                                placeholder="Happ"
                                value={app.name}
                                onChange={(e) =>
                                  updateApp(index, { name: e.target.value })
                                }
                              />
                            </FormControl>
                            <FormControl
                              flex="1 1 140px"
                              minW="120px"
                              isInvalid={!app.scheme.trim()}
                              isRequired
                            >
                              <FormLabel fontSize="sm">
                                {t("appSettings.scheme")}
                              </FormLabel>
                              <Input
                                placeholder="happ"
                                value={app.scheme}
                                onChange={(e) =>
                                  updateApp(index, { scheme: e.target.value })
                                }
                              />
                            </FormControl>
                          </HStack>
                          <Text
                            fontSize="xs"
                            color="gray.500"
                            textTransform="uppercase"
                            fontWeight="semibold"
                            letterSpacing="wide"
                          >
                            {t("appSettings.links")}
                          </Text>
                          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
                            {LINK_KEYS.map((key) => (
                              <FormControl key={key}>
                                <FormLabel fontSize="sm">
                                  {t(`appSettings.link.${key}`)}
                                </FormLabel>
                                <Input
                                  size="sm"
                                  placeholder="https://…"
                                  value={app.links[key] ?? ""}
                                  onChange={(e) =>
                                    updateLink(index, key, e.target.value)
                                  }
                                />
                              </FormControl>
                            ))}
                          </SimpleGrid>
                        </VStack>
                      </AccordionPanel>
                    </AccordionItem>
                  ))}
                </Accordion>
              )}

              <Button alignSelf="flex-start" size="sm" onClick={addApp}>
                {t("appSettings.addApp")}
              </Button>
            </VStack>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack>
            <Button
              variant="outline"
              onClick={resetToDefaults}
              isLoading={loading}
            >
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
