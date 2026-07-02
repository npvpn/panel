import { InputGroup } from "@chakra-ui/react";
import { HostsInput } from "./HostsInput";
import { RHFField } from "./RHFField";

type RHFInputProps = {
  label: React.ReactNode;
  error?: any;
  isInvalid?: boolean;
  registerProps: any;
  placeholder?: string;
  type?: string;

  rightElement?: React.ReactNode;

  formControlProps?: any;
  formLabelProps?: any;
  inputProps?: any;
};

export const RHFInput = ({
  registerProps,
  placeholder,
  type,
  inputProps,
  ...props
}: RHFInputProps) => (
  <RHFField {...props}>
    <InputGroup>
      <HostsInput
        {...registerProps}
        {...inputProps}
        placeholder={placeholder}
        type={type}
      />
    </InputGroup>
  </RHFField>
);
