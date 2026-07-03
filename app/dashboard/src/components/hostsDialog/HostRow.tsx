import {
  Text,
  VStack,
  HStack,
  Accordion,
  AccordionItem,
  AccordionIcon,
  AccordionButton,
  Container,
  Switch,
  Tooltip,
  IconButton,
} from "@chakra-ui/react";
import { NodeType } from "contexts/NodesContext";
import { motion } from "framer-motion";
import { memo } from "react";
import { Controller, useFormContext } from "react-hook-form";
import { Bot } from "types/Bot";
import { DuplicateIcon, DownIcon, UpIcon } from "./constants";
import { DeleteIcon } from "components/DeleteUserModal";
import { RHFInput } from "./RHFInput";
import { HostInfoPopover } from "./HostInfoPopover";
import { HostAdvancedOptions } from "./HostAdvancedOptions";
import { hostsSchema } from "./schema";
import { z } from "zod";

type HostRowProps = {
  hostKey: string;
  index: number;
  hostId: string;
  bots: Bot[];
  nodes: NodeType[];
  inboundPort?: number;
  accordionErrors?: any;
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
  const { register, control } = useFormContext<z.infer<typeof hostsSchema>>();
  const {
    hostKey,
    index,
    hostId,
    bots,
    nodes,
    inbound,
    accordionErrors,
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
            {({ isExpanded }) => (
              <>
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

                {isExpanded && (
                  <HostAdvancedOptions
                    hostKey={hostKey}
                    index={index}
                    inbound={inbound}
                    register={register}
                    control={control}
                    accordionErrors={accordionErrors}
                    t={t}
                    bots={bots}
                    nodes={nodes}
                    proxyHostSecurity={proxyHostSecurity}
                    proxyALPN={proxyALPN}
                    proxyFingerprint={proxyFingerprint}
                  />
                )}
              </>
            )}
          </AccordionItem>
        </Accordion>
      </VStack>
    </motion.div>
  );
});
