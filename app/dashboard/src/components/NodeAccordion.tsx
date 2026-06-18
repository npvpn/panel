import {
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react";
import { FetchNodesQueryKey, NodeType, useNodes } from "contexts/NodesContext";
import { FC, memo } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "react-query";
import "slick-carousel/slick/slick-theme.css";
import "slick-carousel/slick/slick.css";
import { Status } from "types/User";
import { ReloadIcon } from "./Filters";
import { NodeModalStatusBadge } from "./NodeModalStatusBadge";
import { NodeAccordionForm } from "./NodeAccordionForm";

type AccordionInboundType = {
  onToggle: (index: number) => void;
  index: number;
  node: NodeType;
  isOpen: boolean;
  nodeSettings?: {
    min_node_version: string;
    certificate: string;
  };
};

export const NodeAccordion: FC<AccordionInboundType> = memo(
  ({ onToggle, index, node, isOpen, nodeSettings }) => {
    const { reconnectNode, setDeletingNode } = useNodes();
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const handleDeleteNode = setDeletingNode.bind(null, node);

    const { isLoading: isReconnecting, mutate: reconnect } = useMutation(
      reconnectNode.bind(null, node),
      {
        onSuccess: () => {
          queryClient.invalidateQueries(FetchNodesQueryKey);
        },
      }
    );

    const nodeStatus: Status = isReconnecting
      ? "connecting"
      : node.status
      ? node.status
      : "error";

    return (
      <AccordionItem
        border="1px solid"
        _dark={{ borderColor: "gray.600" }}
        _light={{ borderColor: "gray.200" }}
        borderRadius="4px"
        p={1}
        w="full"
      >
        <AccordionButton
          px={2}
          borderRadius="3px"
          onClick={() => onToggle(index)}
        >
          <HStack w="full" justifyContent="space-between" pr={2}>
            <Text
              as="span"
              fontWeight="medium"
              fontSize="sm"
              flex="1"
              textAlign="left"
              color="gray.700"
              _dark={{ color: "gray.300" }}
            >
              {node.name}
            </Text>
            <HStack>
              {node.xray_version && (
                <Badge
                  colorScheme="blue"
                  rounded="full"
                  display="inline-flex"
                  px={3}
                  py={1}
                >
                  <Text
                    textTransform="capitalize"
                    fontSize="0.7rem"
                    fontWeight="medium"
                    letterSpacing="tighter"
                  >
                    Xray {node.xray_version}
                  </Text>
                </Badge>
              )}
              {node.status && (
                <NodeModalStatusBadge status={nodeStatus} compact />
              )}
            </HStack>
          </HStack>
          <AccordionIcon />
        </AccordionButton>
        <AccordionPanel px={2} pb={2}>
          <VStack pb={3} alignItems="flex-start">
            {nodeStatus === "error" && (
              <Alert status="error" size="xs">
                <Box>
                  <HStack w="full">
                    <AlertIcon w={4} />
                    <Text marginInlineEnd={0}>{node.message}</Text>
                  </HStack>
                  <HStack justifyContent="flex-end" w="full">
                    <Button
                      size="sm"
                      aria-label="reconnect node"
                      leftIcon={<ReloadIcon />}
                      onClick={() => reconnect()}
                      disabled={isReconnecting}
                    >
                      {isReconnecting
                        ? t("nodes.reconnecting")
                        : t("nodes.reconnect")}
                    </Button>
                  </HStack>
                </Box>
              </Alert>
            )}
          </VStack>
          {isOpen && (
            <NodeAccordionForm
              node={node}
              nodeSettings={nodeSettings}
              onDelete={handleDeleteNode}
            />
          )}
        </AccordionPanel>
      </AccordionItem>
    );
  }
);
