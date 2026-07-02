import {
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  Text,
} from "@chakra-ui/react";
import React, { FC, useEffect, useMemo } from "react";
import { useFormContext } from "react-hook-form";
import "slick-carousel/slick/slick.css";
import { Bot } from "types/Bot";
import { z } from "zod";
import { useDashboard } from "../contexts/DashboardContext";
import { NodeType } from "../contexts/NodesContext";
import { hostsSchema } from "./hostsDialog/schema";
import { AccordionInboundContent } from "./hostsDialog/AccordionInboundContent";

type AccordionInboundType = {
  hostKey: string;
  isOpen: boolean;
  bots: Bot[];
  nodes: NodeType[];
  toggleAccordion: () => void;
};

export const AccordionInbound: FC<AccordionInboundType> = React.memo(
  ({ hostKey, isOpen, bots, nodes, toggleAccordion }) => {
    const { inbounds } = useDashboard();

    const inbound = useMemo(
      () =>
        Array.from(inbounds.values())
          .flat()
          .find((i) => i.tag === hostKey),
      [inbounds, hostKey]
    );

    const form = useFormContext<z.infer<typeof hostsSchema>>();
    const { errors } = form.formState;
    const accordionErrors = errors[hostKey];

    useEffect(() => {
      if (accordionErrors && !isOpen) {
        toggleAccordion();
      }
    }, [accordionErrors, isOpen, toggleAccordion]);

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
          <AccordionInboundContent
            hostKey={hostKey}
            bots={bots}
            nodes={nodes}
            inbound={inbound}
            accordionErrors={accordionErrors}
          />
        )}
      </AccordionItem>
    );
  }
);

AccordionInbound.displayName = "AccordionInbound";
