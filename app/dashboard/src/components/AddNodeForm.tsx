import {
  AccordionButton,
  AccordionItem,
  AccordionPanel,
  chakra,
  Text,
  useToast,
} from "@chakra-ui/react";
import { PlusIcon as HeroIconPlusIcon } from "@heroicons/react/24/outline";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FetchNodesQueryKey,
  getNodeDefaultValues,
  NodeSchema,
  NodeType,
  useNodes,
} from "contexts/NodesContext";
import { FC } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "react-query";
import "slick-carousel/slick/slick-theme.css";
import "slick-carousel/slick/slick.css";
import {
  generateErrorMessage,
  generateSuccessMessage,
} from "utils/toastHandler";
import { NodeForm } from "./NodeForm";

type AddNodeFormType = {
  toggleAccordion: () => void;
  resetAccordions: () => void;
  isOpen: boolean;
};

const PlusIcon = chakra(HeroIconPlusIcon, {
  baseStyle: {
    w: 5,
    h: 5,
    strokeWidth: 2,
  },
});

export const AddNodeForm: FC<AddNodeFormType> = ({
  toggleAccordion,
  resetAccordions,
  isOpen,
}) => {
  const toast = useToast();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { addNode } = useNodes();
  const form = useForm<NodeType>({
    resolver: zodResolver(NodeSchema),
    defaultValues: {
      ...getNodeDefaultValues(),
      add_as_new_host: false,
    },
  });
  const { isLoading, mutate } = useMutation(addNode, {
    onSuccess: () => {
      generateSuccessMessage(
        t("nodes.addNodeSuccess", { name: form.getValues("name") }),
        toast
      );
      queryClient.invalidateQueries(FetchNodesQueryKey);
      form.reset();
      resetAccordions();
    },
    onError: (e) => {
      generateErrorMessage(e, toast, form);
    },
  });

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
          display="flex"
          gap={1}
        >
          <PlusIcon display={"inline-block"} />{" "}
          <span>{t("nodes.addNewMarzbanNode")}</span>
        </Text>
      </AccordionButton>
      <AccordionPanel px={2} py={4}>
        {isOpen && (
          <NodeForm
            form={form}
            mutate={mutate}
            isLoading={isLoading}
            submitBtnText={t("nodes.addNode")}
            btnProps={{ variant: "solid" }}
            addAsHost
          />
        )}
      </AccordionPanel>
    </AccordionItem>
  );
};
