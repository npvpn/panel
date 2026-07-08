import { Button, AccordionPanel, VStack } from "@chakra-ui/react";
import { FC, useCallback } from "react";
import { useFieldArray, useFormContext } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { Bot } from "types/Bot";
import {
  proxyALPN,
  proxyFingerprint,
  proxyHostSecurity,
} from "constants/Proxies";
import { NodeType } from "contexts/NodesContext";
import { hostsSchema } from "./schema";
import { HostRow } from "./HostRow";

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
  xhttp_extra: "",
  bot_usernames: [],
  node_ids: [],
};

type Props = {
  hostKey: string;
  bots: Bot[];
  nodes: NodeType[];
  inbound: any;
  accordionErrors: any;
};

export const AccordionInboundContent: FC<Props> = ({
  hostKey,
  bots,
  nodes,
  inbound,
  accordionErrors,
}) => {
  const { t } = useTranslation();
  const form = useFormContext<z.infer<typeof hostsSchema>>();

  const {
    fields: hosts,
    append,
    remove,
    insert,
    move,
  } = useFieldArray({
    control: form.control,
    name: hostKey,
  });

  const handleAddHost = useCallback(() => {
    append(EMPTY_HOST);
  }, [append]);

  const duplicateHost = useCallback(
    (index: number) => {
      const value = form.getValues(`${hostKey}.${index}`);
      if (!value) return;

      insert(index + 1, structuredClone(value));
    },
    [form, hostKey, insert]
  );

  const moveHostPosition = useCallback(
    (index: number, direction: "up" | "down") => {
      if (direction === "up" && index > 0) {
        move(index, index - 1);
      } else if (direction === "down" && index < hosts.length - 1) {
        move(index, index + 1);
      }
    },
    [move, hosts.length]
  );

  const removeHost = useCallback(
    (index: number) => {
      remove(index);
    },
    [remove]
  );

  return (
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
            removeHost={removeHost}
            bots={bots}
            nodes={nodes}
            inbound={inbound}
            inboundPort={inbound?.port}
            accordionErrors={accordionErrors}
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
  );
};
