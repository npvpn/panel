import { Checkbox, FormControl, FormLabel } from "@chakra-ui/react";
import { Error } from "./constants";

export const RHFCheckbox = ({ label, registerProps, error }: any) => (
  <FormControl isInvalid={!!error}>
    <Checkbox {...registerProps}>{label}</Checkbox>
    {error && <Error>{error.message}</Error>}
  </FormControl>
);
