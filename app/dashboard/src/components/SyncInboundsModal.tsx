import {
  Button,
  chakra,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Text,
  useToast,
} from "@chakra-ui/react";
import { FC, useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { Icon } from "./Icon";
import { useDashboard } from "contexts/DashboardContext";
import { useTranslation } from "react-i18next";

export const SyncIcon = chakra(ArrowPathIcon, {
  baseStyle: {
    w: 5,
    h: 5,
  },
});

export const SyncInboundsModal: FC = () => {
  const [loading, setLoading] = useState(false);
  const {
    isConfirmingSyncInbounds,
    onConfirmingSyncInbounds,
    syncInbounds,
  } = useDashboard();
  const { t } = useTranslation();
  const toast = useToast();

  const onClose = () => {
    if (loading) return;
    onConfirmingSyncInbounds(false);
  };

  const onConfirm = () => {
    setLoading(true);
    syncInbounds()
      .then(() => {
        toast({
          title: t("syncInboundsConfirm.success"),
          status: "success",
          isClosable: true,
          position: "top",
          duration: 3000,
        });
        onConfirmingSyncInbounds(false);
      })
      .catch(() => {
        toast({
          title: t("syncInboundsConfirm.error"),
          status: "error",
          isClosable: true,
          position: "top",
          duration: 3000,
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <Modal
      isCentered
      isOpen={isConfirmingSyncInbounds}
      onClose={onClose}
      size="sm"
    >
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3">
        <ModalHeader pt={6}>
          <Icon color="orange">
            <SyncIcon />
          </Icon>
        </ModalHeader>
        <ModalCloseButton mt={3} />
        <ModalBody>
          <Text fontWeight="semibold" fontSize="lg">
            {t("syncInboundsConfirm.title")}
          </Text>
          <Text
            mt={1}
            fontSize="sm"
            _dark={{ color: "gray.400" }}
            color="gray.600"
          >
            {t("syncInboundsConfirm.prompt")}
          </Text>
        </ModalBody>
        <ModalFooter display="flex">
          <Button
            size="sm"
            onClick={onClose}
            mr={3}
            w="full"
            variant="outline"
            isDisabled={loading}
          >
            {t("cancel")}
          </Button>
          <Button
            size="sm"
            w="full"
            colorScheme="orange"
            onClick={onConfirm}
            leftIcon={loading ? <Spinner size="xs" /> : undefined}
            isDisabled={loading}
          >
            {t("syncInboundsConfirm.confirm")}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
