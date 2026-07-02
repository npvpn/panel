import {
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Button,
  Text,
  VStack,
} from "@chakra-ui/react";
import React, { FC, useCallback, useEffect, useMemo } from "react";
import { useFieldArray, useFormContext } from "react-hook-form";
import { useTranslation } from "react-i18next";
import "slick-carousel/slick/slick.css";
import { Bot } from "types/Bot";
import { z } from "zod";
import { useDashboard } from "../contexts/DashboardContext";
import { NodeType } from "../contexts/NodesContext";
import { hostsSchema } from "./hostsDialog/schema";
import { HostRow } from "./hostsDialog/HostRow";
import {
  proxyALPN,
  proxyFingerprint,
  proxyHostSecurity,
} from "constants/Proxies";

type AccordionInboundType = {
  hostKey: string;
  isOpen: boolean;
  bots: Bot[];
  nodes: NodeType[];
  toggleAccordion: () => void;
};

const EMPTY_HOST = {
  host: "",
  sni: "",
  port: null,
  path: null,
  address: "",
  remark: "",
  mux_enable: false,
  allowinsecure: false,
  is_disabled: false,
  fragment_setting: "",
  noise_setting: "",
  random_user_agent: false,
  security: "inbound_default",
  alpn: "",
  fingerprint: "",
  use_sni_as_host: false,
  bot_usernames: [],
  node_ids: [],
};

export const AccordionInbound: FC<AccordionInboundType> = React.memo(
  ({ hostKey, isOpen, bots, nodes, toggleAccordion }) => {
    const { inbounds } = useDashboard();

    const inbound = Array.from(inbounds.values())
      .flat()
      .find((i) => i.tag === hostKey);

    const form = useFormContext<z.infer<typeof hostsSchema>>();
    const {
      fields: hosts,
      append: addHost,
      remove: removeHost,
      insert: insertHost,
      move: moveHost,
    } = useFieldArray({
      control: form.control,
      name: hostKey,
    });

    const { errors } = form.formState;
    const { t } = useTranslation();
    const accordionErrors = errors[hostKey];

    const handleAddHost = useCallback(() => {
      addHost(EMPTY_HOST);
    }, [addHost]);

    const duplicateHost = useCallback(
      (index: number) => {
        const value = form.getValues(`${hostKey}.${index}`);
        if (!value) return;
        insertHost(index + 1, structuredClone(value));
      },
      [form, insertHost, hostKey]
    );

    useEffect(() => {
      if (accordionErrors && !isOpen) {
        toggleAccordion();
      }
    }, [accordionErrors, isOpen, toggleAccordion]);

    const moveHostPosition = useCallback(
      (index: number, direction: "up" | "down") => {
        if (direction === "up" && index > 0) {
          moveHost(index, index - 1);
        } else if (direction === "down" && index < hosts.length - 1) {
          moveHost(index, index + 1);
        }
      },
      [moveHost, hosts.length]
    );

    const removeHostCallback = useCallback(
      (index: number) => {
        removeHost(index);
      },
      [removeHost]
    );

    return (
      <AccordionItem
        border="1px solid"
        _dark={{ borderColor: "gray.600" }}
        _light={{ borderColor: "gray.200" }}
        borderRadius="4px"
        p={1}
        w="full"
      >
        <AccordionButton px={2} borderRadius="3px" onClick={toggleAccordion}>
          <Text
            as="span"
            fontWeight="medium"
            fontSize="sm"
            flex="1"
            textAlign="left"
            color="gray.700"
            _dark={{ color: "gray.300" }}
          >
            {hostKey}
          </Text>
          <AccordionIcon />
        </AccordionButton>
        {isOpen && (
          <AccordionPanel px={2} pb={2}>
            <VStack gap={3}>
              {hosts.map((host, index) => (
                <HostRow
                  key={host.id}
                  hostId={host.id}
                  hostKey={hostKey}
                  index={index}
                  hostsLength={hosts.length}
                  duplicateHost={duplicateHost}
                  moveHostPosition={moveHostPosition}
                  removeHost={removeHostCallback}
                  bots={bots}
                  nodes={nodes}
                  inbound={inbound}
                  inboundPort={inbound?.port}
                  accordionErrors={accordionErrors}
                  register={form.register}
                  control={form.control}
                  proxyHostSecurity={proxyHostSecurity}
                  proxyALPN={proxyALPN}
                  proxyFingerprint={proxyFingerprint}
                  t={t}
                />
              ))}

              <Button
                variant="outline"
                type="button"
                w="full"
                size="sm"
                fontWeight="normal"
                onClick={handleAddHost}
              >
                {t("hostsDialog.addHost")}
              </Button>
            </VStack>
          </AccordionPanel>
        )}
      </AccordionItem>
    );
  }
);

AccordionInbound.displayName = "AccordionInbound";
