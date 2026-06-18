import {
  Accordion,
  Box,
  Button,
  chakra,
  Collapse,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
} from "@chakra-ui/react";
import { ChevronDownIcon, SquaresPlusIcon } from "@heroicons/react/24/outline";
import { useNodesQuery } from "contexts/NodesContext";
import { FC, useCallback, useEffect, useMemo, useState } from "react";

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
import { PlusIcon as HeroIconPlusIcon } from "@heroicons/react/24/outline";

const ModalIcon = chakra(SquaresPlusIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});
const PlusIcon = chakra(HeroIconPlusIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    strokeWidth: 2,
  },
});

export const NodesDialog: FC = () => {
  const [isAddingNode, setIsAddingNode] = useState(false);
  const { isEditingNodes, onEditingNodes } = useDashboard();
  const { t } = useTranslation();
  const [openAccordions, setOpenAccordions] = useState<Set<number>>(new Set());
  const { data: nodes, isLoading } = useNodesQuery();

  useEffect(() => {
    if (isEditingNodes) {
      const scrollbarWidth =
        window.innerWidth - document.documentElement.clientWidth;
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    } else {
      document.body.style.paddingRight = "";
    }
    return () => {
      document.body.style.paddingRight = "";
    };
  }, [isEditingNodes]);

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

  const openIndexes = useMemo(
    () => Array.from(openAccordions),
    [openAccordions]
  );

  return (
    <>
      <Modal
        isOpen={isEditingNodes}
        onClose={onClose}
        size="2xl"
        scrollBehavior="inside"
      >
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3" w="full" maxW="2xl">
          <ModalHeader pt={6} pb={4}>
            <HStack spacing={4} align="center">
              <Icon color="primary">
                <ModalIcon color="white" />
              </Icon>

              <Box>
                <Text fontSize="lg" fontWeight="semibold">
                  {t("header.nodeSettings")}
                </Text>

                <Text
                  fontSize="sm"
                  opacity={0.6}
                  mt={1}
                  maxW="490px"
                  lineHeight="1.4"
                >
                  {t("nodes.title")}
                </Text>
              </Box>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody w="full" pb={6} pt={3}>
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

            <Button
              w="full"
              mb={3}
              variant="outline"
              leftIcon={<HeroIconPlusIcon width="20px" strokeWidth={2} />}
              rightIcon={
                <ChevronDownIcon
                  width="16px"
                  style={{
                    transform: isAddingNode ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s ease",
                  }}
                />
              }
              onClick={() => setIsAddingNode((prev) => !prev)}
            >
              {t("nodes.addNewMarzbanNode")}
            </Button>

            <Collapse in={isAddingNode} animateOpacity>
              <AddNodeForm
                isOpen={isAddingNode}
                resetAccordions={() => {
                  setOpenAccordions(new Set());
                  setIsAddingNode(false);
                }}
              />
            </Collapse>

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
                        key={node.id ?? node.name}
                        node={node}
                        isOpen={isOpen}
                        nodeSettings={nodeSettings}
                      />
                    );
                  })}
              </VStack>
            </Accordion>
          </ModalBody>
        </ModalContent>
      </Modal>
      <DeleteNodeModal deleteCallback={() => setOpenAccordions(new Set())} />
    </>
  );
};
