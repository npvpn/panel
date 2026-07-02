import {
  Accordion,
  Button,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useHosts } from "contexts/HostsContext";
import { FC, useCallback, useEffect, useMemo, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";
import "slick-carousel/slick/slick-theme.css";
import "slick-carousel/slick/slick.css";
import { Bot } from "types/Bot";
import { z } from "zod";
import { useDashboard } from "../contexts/DashboardContext";
import { NodeType } from "../contexts/NodesContext";
import { Icon } from "./Icon";
import { hostsSchema } from "./hostsDialog/schema";
import { ModalIcon } from "./hostsDialog/constants";
import { AccordionInbound } from "./AccordionInbound";

export const HostsDialog: FC = () => {
  const { isEditingHosts, onEditingHosts, refetchUsers, inbounds } =
    useDashboard();
  const { isLoading, hosts, fetchHosts, isPostLoading, setHosts } = useHosts();
  const toast = useToast();
  const { t } = useTranslation();
  const [openAccordions, setOpenAccordions] = useState<number[]>([]);
  const [bots, setBots] = useState<Bot[]>([]);
  const [nodes, setNodes] = useState<NodeType[]>([]);

  const hostKeys = useMemo(() => {
    return hosts ? Object.keys(hosts) : [];
  }, [hosts]);

  const memoizedBots = useMemo(() => bots, [bots]);
  const memoizedNodes = useMemo(() => nodes, [nodes]);

  useEffect(() => {
    if (!isEditingHosts) return;

    const loadData = async () => {
      try {
        await fetchHosts();
        const [botsData, nodesData] = await Promise.all([
          fetch<Bot[]>("/bots").catch(() => [] as Bot[]),
          fetch<NodeType[]>("/nodes").catch(() => [] as NodeType[]),
        ]);
        setBots(botsData);
        setNodes(nodesData);
      } catch (error) {
        console.error("Failed to load data:", error);
      }
    };

    loadData();
  }, [isEditingHosts, fetchHosts]);

  const form = useForm<z.infer<typeof hostsSchema>>({
    resolver: zodResolver(hostsSchema),
  });

  useEffect(() => {
    if (hosts && isEditingHosts) {
      form.reset(hosts);
    }
  }, [hosts, isEditingHosts, form]);

  const onClose = useCallback(() => {
    setOpenAccordions([]);
    onEditingHosts(false);
  }, [onEditingHosts]);

  const handleFormSubmit = useCallback(
    (hostsData: z.infer<typeof hostsSchema>) => {
      setHosts(hostsData)
        .then(() => {
          toast({
            title: t("hostsDialog.savedSuccess"),
            status: "success",
            isClosable: true,
            position: "top",
            duration: 3000,
          });
          refetchUsers();
          onClose();
        })
        .catch((err) => {
          if (err?.response?.status === 409 || err?.response?.status === 400) {
            toast({
              title: err.response?._data?.detail,
              status: "error",
              isClosable: true,
              position: "top",
              duration: 3000,
            });
          }
          if (err?.response?.status === 422) {
            Object.keys(err.response._data.detail).forEach((key) => {
              toast({
                title: err.response._data.detail[key] + " (" + key + ")",
                status: "error",
                isClosable: true,
                position: "top",
                duration: 3000,
              });
            });
          }
        });
    },
    [setHosts, toast, t, refetchUsers, onClose]
  );

  const toggleAccordion = useCallback((index: number) => {
    setOpenAccordions((prev) => {
      if (prev.includes(index)) {
        return prev.filter((i) => i !== index);
      }
      return [...prev, index];
    });
  }, []);

  const handleAccordionToggle = useCallback(
    (index: number) => {
      return () => toggleAccordion(index);
    },
    [toggleAccordion]
  );

  const isAccordionOpen = useCallback(
    (index: number) => {
      return openAccordions.includes(index);
    },
    [openAccordions]
  );

  const accordionProps = useMemo(
    () => ({
      w: "full",
      allowToggle: true,
      allowMultiple: true,
      index: openAccordions,
    }),
    [openAccordions]
  );

  const renderContent = useMemo(() => {
    if (isLoading) {
      return t("hostsDialog.loading");
    }

    if (!hosts || hostKeys.length === 0) {
      return "No inbound found. Please check your Xray config file.";
    }

    return (
      <Accordion {...accordionProps}>
        <VStack w="full">
          {hostKeys.map((hostKey, index) => (
            <AccordionInbound
              key={hostKey}
              hostKey={hostKey}
              isOpen={isAccordionOpen(index)}
              toggleAccordion={() => toggleAccordion(index)}
              bots={memoizedBots}
              nodes={memoizedNodes}
            />
          ))}
        </VStack>
      </Accordion>
    );
  }, [
    isLoading,
    hosts,
    hostKeys,
    accordionProps,
    isAccordionOpen,
    handleAccordionToggle,
    bots,
    nodes,
    t,
  ]);

  return (
    <Modal isOpen={isEditingHosts} onClose={onClose}>
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3" w="fit-content" maxW="3xl">
        <ModalHeader pt={6}>
          <Icon color="primary">
            <ModalIcon color="white" />
          </Icon>
        </ModalHeader>
        <ModalCloseButton mt={3} />
        <ModalBody w="440px" pb={3} pt={3}>
          <FormProvider {...form}>
            <form onSubmit={form.handleSubmit(handleFormSubmit)}>
              <Text mb={3} opacity={0.8} fontSize="sm">
                {t("hostsDialog.title")}
              </Text>
              {renderContent}
              <HStack justifyContent="flex-end" py={2}>
                <Button
                  variant="solid"
                  mt="2"
                  type="submit"
                  colorScheme="primary"
                  size="sm"
                  px={5}
                  isLoading={isPostLoading}
                  disabled={isPostLoading}
                >
                  {t("hostsDialog.apply")}
                </Button>
              </HStack>
            </form>
          </FormProvider>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
