import { Box, useToast } from "@chakra-ui/react";
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
  resetAccordions: () => void;
  isOpen: boolean;
};

export const AddNodeForm: FC<AddNodeFormType> = ({
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
    <Box
      border="1px solid"
      _dark={{ borderColor: "gray.600" }}
      _light={{ borderColor: "gray.200" }}
      borderRadius="4px"
      p={3}
      w="full"
    >
      <NodeForm
        form={form}
        mutate={mutate}
        isLoading={isLoading}
        submitBtnText={t("nodes.addNode")}
        btnProps={{ variant: "solid" }}
        addAsHost
      />
    </Box>
  );
};
