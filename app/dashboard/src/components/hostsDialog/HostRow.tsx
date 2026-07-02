import {
  Box,
  FormControl,
  Text,
  InputGroup,
  InputRightElement,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverTrigger,
  Portal,
  VStack,
  Badge,
  HStack,
  Accordion,
  AccordionItem,
  AccordionPanel,
  Button,
  Checkbox,
  AccordionIcon,
  FormLabel,
  AccordionButton,
  Container,
  Switch,
  Tooltip,
  IconButton,
} from "@chakra-ui/react";
import { NodeType } from "contexts/NodesContext";
import { motion } from "framer-motion";
import { ChangeEvent, memo } from "react";
import { Control, Controller, UseFormRegister } from "react-hook-form";
import { Bot } from "types/Bot";
import {
  InfoIcon,
  Error,
  Select,
  DuplicateIcon,
  DownIcon,
  UpIcon,
} from "./constants";
import { DeleteIcon } from "components/DeleteUserModal";
import { Trans } from "react-i18next";
import { HostsInput } from "./HostsInput";
import { RHFInput } from "./RHFInput";
import { HostInfoPopover } from "./HostInfoPopover";
import { RHFCheckbox } from "./RHFCheckbox";
import { RHFSelect } from "./RHFSelect";

type HostRowProps = {
  hostKey: string;
  index: number;
  hostId: string;
  bots: Bot[];
  nodes: NodeType[];

  inboundPort?: number;

  accordionErrors?: any;

  register: UseFormRegister<any>;
  control: Control<any>;

  t: (key: string, opts?: any) => string;

  duplicateHost: (index: number) => void;
  moveHostPosition: (index: number, direction: "up" | "down") => void;
  removeHost: (index: number) => void;

  hostsLength: number;
  inbound: any;

  proxyHostSecurity: any[];
  proxyALPN: any[];
  proxyFingerprint: any[];
};

export const HostRow = memo(function HostRow(props: HostRowProps) {
  const {
    hostKey,
    index,
    hostId,
    bots,
    nodes,
    inbound,
    accordionErrors,

    register,
    control,

    t,

    duplicateHost,
    moveHostPosition,
    removeHost,

    hostsLength,
    proxyHostSecurity,
    proxyALPN,
    proxyFingerprint,
  } = props;

  return (
    <motion.div
      key={hostId}
      layout
      initial={false}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{
        layout: { type: "spring", stiffness: 500, damping: 30 },
        opacity: { duration: 0.1 },
      }}
      id={hostId}
      whileDrag={{ scale: 1.05, zIndex: 10 }}
      style={{ width: "100%" }}
    >
      <VStack border="1px solid" p={2} w="full" borderRadius="4px">
        <HStack w="100%" alignItems="flex-start">
          <RHFInput
            label="Remark"
            registerProps={register(`${hostKey}.${index}.remark`)}
            error={accordionErrors?.[index]?.remark}
            rightElement={<HostInfoPopover t={t} />}
            formControlProps={{
              position: "relative",
              zIndex: 10,
            }}
            inputProps={{
              size: "sm",
              borderRadius: "4px",
            }}
          />
        </HStack>

        <RHFInput
          label="Address"
          registerProps={register(`${hostKey}.${index}.address`)}
          error={accordionErrors?.[index]?.address}
          placeholder="example.com"
          rightElement={<HostInfoPopover t={t} />}
          formControlProps={{
            isInvalid: !!accordionErrors?.[index]?.address,
          }}
        />

        <Accordion w="full" allowToggle>
          <AccordionItem border="0">
            <div style={{ display: "flex", alignItems: "center" }}>
              <AccordionButton
                display="flex"
                px={0}
                py={1}
                borderRadius={3}
                _hover={{ bg: "transparent" }}
              >
                <Text
                  flex="3"
                  align="start"
                  fontSize="xs"
                  color="gray.600"
                  _dark={{ color: "gray.500" }}
                  pl={1}
                >
                  {t("hostsDialog.advancedOptions")}
                  <AccordionIcon fontSize="sm" ml={1} />
                </Text>

                <Container flex="1" px="0" display={"contents"}>
                  <Controller
                    control={control}
                    name={`${hostKey}.${index}.is_disabled`}
                    render={({ field }) => {
                      return (
                        <Switch
                          mx="1.5"
                          colorScheme="primary"
                          isChecked={!!field.value}
                          onChange={(e) => field.onChange(e.target.checked)}
                        />
                      );
                    }}
                  />
                  <Tooltip label="Delete" placement="top">
                    <IconButton
                      aria-label="Delete"
                      size="sm"
                      colorScheme="red"
                      variant="ghost"
                      onClick={removeHost.bind(null, index)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </Container>
              </AccordionButton>
              <Tooltip label="Duplicate" placement="top">
                <IconButton
                  aria-label="Duplicate"
                  size="sm"
                  colorScheme="white"
                  variant="ghost"
                  onClick={() => duplicateHost(index)}
                >
                  <DuplicateIcon />
                </IconButton>
              </Tooltip>
              {index < hostsLength - 1 && (
                <Tooltip label="Move Down" placement="top">
                  <IconButton
                    aria-label="DownIcon"
                    size="sm"
                    colorScheme="white"
                    variant="ghost"
                    onClick={() => moveHostPosition(index, "down")}
                  >
                    <DownIcon />
                  </IconButton>
                </Tooltip>
              )}
              {index > 0 && (
                <Tooltip label="Move Up" placement="top">
                  <IconButton
                    aria-label="UpIcon"
                    size="sm"
                    colorScheme="white"
                    variant="ghost"
                    onClick={() => moveHostPosition(index, "up")}
                  >
                    <UpIcon />
                  </IconButton>
                </Tooltip>
              )}
            </div>
            <AccordionPanel w="full" p={1}>
              <VStack key={index} w="full" borderRadius="4px">
                <RHFInput
                  label={t("hostsDialog.port")}
                  registerProps={register(`${hostKey}.${index}.port`)}
                  error={accordionErrors?.[index]?.port}
                  placeholder={String(inbound.port || "8080")}
                  type="number"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.port.info")}
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                  formLabelProps={{
                    pb: 1,
                    m: 0,
                    alignItems: "center",
                    gap: 1,
                  }}
                />

                <RHFInput
                  label={t("hostsDialog.sni")}
                  registerProps={register(`${hostKey}.${index}.sni`)}
                  error={accordionErrors?.[index]?.sni}
                  placeholder="SNI (e.g. example.com)"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.sni.info")}
                          </Text>
                          <Text fontSize="xs" mt="2">
                            <Trans
                              i18nKey="hostsDialog.host.wildcard"
                              components={{
                                badge: <Badge />,
                              }}
                            />
                          </Text>
                          <Text fontSize="xs">
                            <Trans
                              i18nKey="hostsDialog.host.multiHost"
                              components={{
                                badge: <Badge />,
                              }}
                            />
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                  formLabelProps={{
                    pb: 1,
                    m: 0,
                    alignItems: "center",
                    gap: 1,
                  }}
                />

                <RHFInput
                  label={t("hostsDialog.host")}
                  registerProps={register(`${hostKey}.${index}.host`)}
                  error={accordionErrors?.[index]?.host}
                  placeholder="Host (e.g. example.com)"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.host.info")}
                          </Text>
                          <Text fontSize="xs" mt="2">
                            <Trans
                              i18nKey="hostsDialog.host.wildcard"
                              components={{
                                badge: <Badge />,
                              }}
                            />
                          </Text>
                          <Text fontSize="xs">
                            <Trans
                              i18nKey="hostsDialog.host.multiHost"
                              components={{
                                badge: <Badge />,
                              }}
                            />
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                />

                <RHFInput
                  label={t("hostsDialog.path")}
                  registerProps={register(`${hostKey}.${index}.path`)}
                  error={accordionErrors?.[index]?.path}
                  placeholder="path (e.g. /vless)"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.path.info")}
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                />

                <RHFSelect
                  label={t("hostsDialog.security")}
                  registerProps={register(`${hostKey}.${index}.security`)}
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.security.info")}
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  formControlProps={{
                    height: "66px",
                  }}
                  selectProps={{
                    size: "sm",
                  }}
                >
                  {proxyHostSecurity.map((s) => {
                    return (
                      <option key={s.value} value={s.value}>
                        {s.title}
                      </option>
                    );
                  })}
                </RHFSelect>

                <RHFSelect
                  label={t("hostsDialog.alpn")}
                  registerProps={register(`${hostKey}.${index}.alpn`)}
                  formControlProps={{
                    height: "66px",
                  }}
                  selectProps={{
                    size: "sm",
                  }}
                >
                  {proxyALPN.map((s) => {
                    return (
                      <option key={s.value} value={s.value}>
                        {s.title}
                      </option>
                    );
                  })}
                </RHFSelect>

                <RHFSelect
                  label={t("hostsDialog.fingerprint")}
                  registerProps={register(`${hostKey}.${index}.fingerprint`)}
                  formControlProps={{
                    height: "66px",
                  }}
                  selectProps={{
                    size: "sm",
                  }}
                >
                  {proxyFingerprint.map((s) => {
                    return (
                      <option key={s.value} value={s.value}>
                        {s.title}
                      </option>
                    );
                  })}
                </RHFSelect>

                <RHFInput
                  label={t("hostsDialog.fragment")}
                  registerProps={register(
                    `${hostKey}.${index}.fragment_setting`
                  )}
                  error={accordionErrors?.[index]?.fragment_setting}
                  placeholder="Fragment settings by pattern"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.fragment.info")}
                          </Text>
                          <Text fontSize="xs" pr={5} pt={2} pb={1}>
                            {t("hostsDialog.fragment.info.examples")}
                          </Text>
                          <Text fontSize="xs" pr={5}>
                            100-200,10-20,tlshello
                          </Text>
                          <Text fontSize="xs" pr={5}>
                            100-200,10-20,1-3
                          </Text>
                          <Text fontSize="xs" pr={5} pt="3">
                            {t("hostsDialog.fragment.info.attention")}
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                />

                <RHFInput
                  label={t("hostsDialog.noise")}
                  registerProps={register(`${hostKey}.${index}.noise_setting`)}
                  error={accordionErrors?.[index]?.noise_setting}
                  placeholder="Noise settings by pattern"
                  rightElement={
                    <Popover isLazy placement="right">
                      <PopoverTrigger>
                        <InfoIcon />
                      </PopoverTrigger>
                      <Portal>
                        <PopoverContent p={2}>
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <Text fontSize="xs" pr={5}>
                            {t("hostsDialog.noise.info")}
                          </Text>
                          <Text fontSize="xs" pr={5} pt={2} pb={1}>
                            {t("hostsDialog.noise.info.examples")}
                          </Text>
                          <Text fontSize="xs" pr={5}>
                            rand:10-20,10-20
                          </Text>
                          <Text fontSize="xs" pr={5}>
                            rand:10-20,10-20&base64:7nQBAAABAAAAAAAABnQtcmluZwZtc2VkZ2UDbmV0AAABAAE=,10-25
                          </Text>
                          <Text fontSize="xs" pr={5} pt="3">
                            {t("hostsDialog.noise.info.attention")}
                          </Text>
                        </PopoverContent>
                      </Portal>
                    </Popover>
                  }
                  inputProps={{
                    size: "sm",
                    borderRadius: "4px",
                  }}
                />

                <RHFCheckbox
                  label={t("hostsDialog.useSniAsHost")}
                  registerProps={register(
                    `${hostKey}.${index}.use_sni_as_host`
                  )}
                  error={accordionErrors?.[index]?.use_sni_as_host}
                />

                <RHFCheckbox
                  label={t("hostsDialog.allowinsecure")}
                  registerProps={register(`${hostKey}.${index}.allowinsecure`)}
                  error={accordionErrors?.[index]?.allowinsecure}
                />

                <RHFCheckbox
                  label={t("hostsDialog.muxEnable")}
                  registerProps={register(`${hostKey}.${index}.mux_enable`)}
                  error={accordionErrors?.[index]?.mux_enable}
                />

                <RHFCheckbox
                  label={t("hostsDialog.randomUserAgent")}
                  registerProps={register(
                    `${hostKey}.${index}.random_user_agent`
                  )}
                  error={accordionErrors?.[index]?.random_user_agent}
                />

                {bots.length > 0 && (
                  <FormControl
                    isInvalid={
                      !!(
                        accordionErrors && accordionErrors[index]?.bot_usernames
                      )
                    }
                  >
                    <FormLabel>{t("hostsDialog.availableBots")}</FormLabel>
                    <Text
                      fontSize="xs"
                      color="gray.600"
                      _dark={{ color: "gray.400" }}
                      mb={2}
                    >
                      {t("hostsDialog.availableBots.info")}
                    </Text>
                    <Controller
                      control={control}
                      name={`${hostKey}.${index}.bot_usernames`}
                      render={({ field }) => {
                        const selectedBotUsernames: string[] = Array.isArray(
                          field.value
                        )
                          ? field.value
                          : [];
                        const selectedBots = bots.filter((bot: Bot) =>
                          selectedBotUsernames.includes(bot.username)
                        );

                        return (
                          <Popover placement="bottom-start">
                            <PopoverTrigger>
                              <Button
                                variant="outline"
                                size="sm"
                                w="full"
                                justifyContent="space-between"
                              >
                                <Text as="span" noOfLines={1}>
                                  {selectedBots.length
                                    ? t("hostsDialog.availableBots.selected", {
                                        count: selectedBots.length,
                                      })
                                    : t("hostsDialog.availableBots.all")}
                                </Text>
                                <AccordionIcon />
                              </Button>
                            </PopoverTrigger>
                            <Portal>
                              <PopoverContent
                                w="280px"
                                maxH="320px"
                                overflowY="auto"
                                zIndex={1500}
                              >
                                <PopoverArrow />
                                <PopoverCloseButton />
                                <PopoverBody pt={8}>
                                  <VStack align="start" spacing={2}>
                                    {bots.map((bot: Bot) => (
                                      <Checkbox
                                        key={bot.username}
                                        isChecked={selectedBotUsernames.includes(
                                          bot.username
                                        )}
                                        onChange={(
                                          event: ChangeEvent<HTMLInputElement>
                                        ) => {
                                          if (event.target.checked) {
                                            field.onChange([
                                              ...selectedBotUsernames,
                                              bot.username,
                                            ]);
                                          } else {
                                            field.onChange(
                                              selectedBotUsernames.filter(
                                                (username: string) =>
                                                  username !== bot.username
                                              )
                                            );
                                          }
                                        }}
                                      >
                                        <Text as="span" fontSize="sm">
                                          @{bot.username}
                                          {bot.title ? ` (${bot.title})` : ""}
                                        </Text>
                                      </Checkbox>
                                    ))}
                                    {selectedBotUsernames.length > 0 && (
                                      <Button
                                        variant="ghost"
                                        size="xs"
                                        onClick={() => field.onChange([])}
                                      >
                                        {t("hostsDialog.availableBots.clear")}
                                      </Button>
                                    )}
                                  </VStack>
                                </PopoverBody>
                              </PopoverContent>
                            </Portal>
                          </Popover>
                        );
                      }}
                    />
                    {accordionErrors &&
                      accordionErrors[index]?.bot_usernames && (
                        <Error>
                          {accordionErrors[index]?.bot_usernames?.message}
                        </Error>
                      )}
                  </FormControl>
                )}
                {nodes.filter((n) => n.id != null).length > 0 && (
                  <FormControl>
                    <FormLabel>{t("hostsDialog.linkedNodes")}</FormLabel>
                    <Text
                      fontSize="xs"
                      color="gray.600"
                      _dark={{ color: "gray.400" }}
                      mb={2}
                    >
                      {t("hostsDialog.linkedNodes.info")}
                    </Text>
                    <Controller
                      control={control}
                      name={`${hostKey}.${index}.node_ids`}
                      render={({ field }) => {
                        const selectedIds: number[] = Array.isArray(field.value)
                          ? field.value
                          : [];
                        return (
                          <Popover isLazy placement="bottom-start">
                            <PopoverTrigger>
                              <Button
                                variant="outline"
                                size="sm"
                                w="full"
                                justifyContent="space-between"
                              >
                                <Text as="span" noOfLines={1}>
                                  {selectedIds.length
                                    ? t("hostsDialog.linkedNodes.selected", {
                                        count: selectedIds.length,
                                      })
                                    : t("hostsDialog.linkedNodes.none")}
                                </Text>
                                <AccordionIcon />
                              </Button>
                            </PopoverTrigger>
                            <Portal>
                              <PopoverContent
                                w="280px"
                                maxH="320px"
                                overflowY="auto"
                                zIndex={1500}
                              >
                                <PopoverArrow />
                                <PopoverCloseButton />
                                <PopoverBody pt={8}>
                                  <VStack align="start" spacing={2}>
                                    {nodes
                                      .filter((n) => n.id != null)
                                      .map((node: NodeType) => {
                                        const nodeId = node.id as number;
                                        return (
                                          <Checkbox
                                            key={nodeId}
                                            isChecked={selectedIds.includes(
                                              nodeId
                                            )}
                                            onChange={(
                                              event: ChangeEvent<HTMLInputElement>
                                            ) => {
                                              if (event.target.checked) {
                                                field.onChange([
                                                  ...selectedIds,
                                                  nodeId,
                                                ]);
                                              } else {
                                                field.onChange(
                                                  selectedIds.filter(
                                                    (id: number) =>
                                                      id !== nodeId
                                                  )
                                                );
                                              }
                                            }}
                                          >
                                            <Text as="span" fontSize="sm">
                                              {node.name}
                                            </Text>
                                          </Checkbox>
                                        );
                                      })}
                                    {selectedIds.length > 0 && (
                                      <Button
                                        variant="ghost"
                                        size="xs"
                                        onClick={() => field.onChange([])}
                                      >
                                        {t("hostsDialog.linkedNodes.clear")}
                                      </Button>
                                    )}
                                  </VStack>
                                </PopoverBody>
                              </PopoverContent>
                            </Portal>
                          </Popover>
                        );
                      }}
                    />
                  </FormControl>
                )}
              </VStack>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>
      </VStack>
    </motion.div>
  );
});
