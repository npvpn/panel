import { Select } from "./constants";
import { RHFField } from "./RHFField";

type RHFSelectProps = {
  label: React.ReactNode;
  error?: any;
  registerProps: any;

  children: React.ReactNode;

  formControlProps?: any;
  formLabelProps?: any;
  selectProps?: any;
  rightElement?: React.ReactNode;
};

export const RHFSelect = ({
  registerProps,
  children,
  selectProps,
  ...props
}: RHFSelectProps) => (
  <RHFField {...props}>
    <Select {...registerProps} {...selectProps}>
      {children}
    </Select>
  </RHFField>
);
