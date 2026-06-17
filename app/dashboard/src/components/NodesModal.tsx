import {
  Accordion,
  Box,
  chakra,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
} from "@chakra-ui/react";
import { SquaresPlusIcon } from "@heroicons/react/24/outline";
import { useNodesQuery } from "contexts/NodesContext";
import { FC, useCallback, useMemo, useState } from "react";

import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import "slick-carousel/slick/slick-theme.css";
import "slick-carousel/slick/slick.css";

import { useDashboard } from "../contexts/DashboardContext";
import { DeleteNodeModal } from "./DeleteNodeModal";
import { Icon } from "./Icon";
import { fetch } from "service/http";
import { NodeAccordion } from "./NodeAccordion";
import { AddNodeForm } from "./AddNodeForm";

const ModalIcon = chakra(SquaresPlusIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});

export const NodesDialog: FC = () => {
  const { isEditingNodes, onEditingNodes } = useDashboard();
  const { t } = useTranslation();
  const [openAccordions, setOpenAccordions] = useState<Set<number>>(new Set());
  const { data: nodes, isLoading } = useNodesQuery();

  const { data: nodeSettings } = useQuery({
    queryKey: ["node-settings"],
    queryFn: () =>
      fetch<{
        min_node_version: string;
        certificate: string;
      }>("/node/settings"),
  });

  const onClose = () => {
    setOpenAccordions(new Set());
    onEditingNodes(false);
  };

  const toggleAccordion = useCallback((index: number) => {
    setOpenAccordions((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const addNodeIndex = (nodes || []).length;

  const openIndexes = useMemo(
    () => Array.from(openAccordions),
    [openAccordions]
  );

  const nodeSettingsMemo = useMemo(() => nodeSettings, [nodeSettings]);

  return (
    <>
      <Modal isOpen={isEditingNodes} onClose={onClose}>
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3" w="fit-content" maxW="3xl">
          <ModalHeader pt={6}>
            <Icon color="primary">
              <ModalIcon color="white" />
            </Icon>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody w="full" maxW="440px" pb={6} pt={3}>
            <Text mb={3} opacity={0.8} fontSize="sm">
              {t("nodes.title")}
            </Text>
            {isLoading && (
              <VStack w="full" spacing={2}>
                <Box
                  w="full"
                  h="40px"
                  bg="gray.100"
                  _dark={{ bg: "gray.700" }}
                  borderRadius="4px"
                />
                <Box
                  w="full"
                  h="40px"
                  bg="gray.100"
                  _dark={{ bg: "gray.700" }}
                  borderRadius="4px"
                />
                <Box
                  w="full"
                  h="40px"
                  bg="gray.100"
                  _dark={{ bg: "gray.700" }}
                  borderRadius="4px"
                />
              </VStack>
            )}

            <Accordion w="full" allowToggle index={openIndexes}>
              <VStack w="full">
                {!isLoading &&
                  nodes &&
                  nodes.map((node, index) => {
                    const isOpen = openAccordions.has(index);

                    return (
                      <NodeAccordion
                        onToggle={toggleAccordion}
                        index={index}
                        key={node.name}
                        node={node as any}
                        isOpen={isOpen}
                        nodeSettings={nodeSettingsMemo}
                      />
                    );
                  })}

                <AddNodeForm
                  isOpen={openAccordions.has(addNodeIndex)}
                  toggleAccordion={() => toggleAccordion((nodes || []).length)}
                  resetAccordions={() => setOpenAccordions(new Set())}
                />
              </VStack>
            </Accordion>
          </ModalBody>
        </ModalContent>
      </Modal>
      <DeleteNodeModal deleteCallback={() => setOpenAccordions(new Set())} />
    </>
  );
};
