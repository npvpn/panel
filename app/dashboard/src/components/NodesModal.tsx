import {
  Box,
  Button,
  chakra,
  Collapse,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
} from "@chakra-ui/react";
import {
  ChevronDownIcon,
  MagnifyingGlassIcon,
  SquaresPlusIcon,
} from "@heroicons/react/24/outline";
import { NodeType, useNodesQuery } from "contexts/NodesContext";
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

export const NodesDialog: FC = () => {
  const [isAddingNode, setIsAddingNode] = useState(false);
  const [search, setSearch] = useState("");
  const { isEditingNodes, onEditingNodes } = useDashboard();
  const { t } = useTranslation();
  const [openAccordion, setOpenAccordion] = useState<number | null>(null);
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
    setOpenAccordion(null);
    onEditingNodes(false);
  };

  const toggleAccordion = useCallback((id: number) => {
    setOpenAccordion((prev) => (prev === id ? null : id));
  }, []);

  const filteredNodes = useMemo(() => {
    if (!nodes) return [];
    if (!search.trim()) return nodes;
    return nodes.filter((node) =>
      node.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [nodes, search]);

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
          <ModalBody
            w="full"
            pb={6}
            pt={3}
            sx={{
              "&::-webkit-scrollbar": {
                width: "6px",
              },
              "&::-webkit-scrollbar-track": {
                background: "transparent",
              },
              "&::-webkit-scrollbar-thumb": {
                background: "rgba(128,128,128,0.4)",
                borderRadius: "999px",
              },
              "&::-webkit-scrollbar-thumb:hover": {
                background: "rgba(128,128,128,0.6)",
              },
            }}
          >
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

            <InputGroup mb={3}>
              <InputLeftElement pointerEvents="none">
                <MagnifyingGlassIcon width="16px" color="gray" />
              </InputLeftElement>
              <Input
                placeholder={t("nodes.search") ?? "Поиск по нодам..."}
                size="md"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </InputGroup>

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
                  setOpenAccordion(null);
                  setIsAddingNode(false);
                }}
              />
            </Collapse>
            {/* <Accordion w="full" allowToggle> */}
            <VStack w="full">
              {!isLoading && filteredNodes.length === 0 && search.trim() && (
                <Text opacity={0.5} fontSize="sm" textAlign="center" py={4}>
                  {t("nodes.notFound") ?? "Ноды не найдены"}
                </Text>
              )}
              {!isLoading &&
                filteredNodes.map((node) => {
                  if (typeof node.id !== "number") return null;

                  const isOpen = openAccordion === node.id;

                  return (
                    <NodeAccordion
                      onToggle={toggleAccordion}
                      key={node.id}
                      node={node}
                      isOpen={isOpen}
                      nodeSettings={nodeSettings}
                    />
                  );
                })}
            </VStack>
            {/* </Accordion> */}
          </ModalBody>
        </ModalContent>
      </Modal>
      <DeleteNodeModal deleteCallback={() => setOpenAccordion(null)} />
    </>
  );
};
