import { z } from "zod";

export const hostsSchema = z.record(
  z.string().min(1),
  z.array(
    z
      .object({
        remark: z.string().min(1, "Remark is required"),
        address: z.string(),
        port: z
          .string()
          .or(z.number())
          .nullable()
          .transform((value) => {
            if (typeof value === "number") return value;
            if (value !== null && !isNaN(parseInt(value)))
              return Number(parseInt(value));
            return null;
          }),
        path: z.string().nullable(),
        sni: z.string().nullable(),
        host: z.string().nullable(),
        mux_enable: z.boolean().default(false),
        allowinsecure: z.boolean().nullable().default(false),
        is_disabled: z.boolean().default(true),
        fragment_setting: z.string().nullable(),
        noise_setting: z.string().nullable(),
        random_user_agent: z.boolean().default(false),
        security: z.string(),
        alpn: z.string(),
        fingerprint: z.string(),
        use_sni_as_host: z.boolean().default(false),
        xhttp_extra: z
          .string()
          .nullable()
          .optional()
          .refine(
            (v) => {
              if (!v) return true;
              try {
                const parsed = JSON.parse(v);
                return (
                  typeof parsed === "object" &&
                  !Array.isArray(parsed) &&
                  parsed !== null
                );
              } catch {
                return false;
              }
            },
            { message: "Must be a valid JSON object" }
          ),
        bot_usernames: z.array(z.string()).default([]),
        node_ids: z.array(z.number()).default([]),
      })
      .superRefine((data, ctx) => {
        if (!data.address && (!data.node_ids || data.node_ids.length === 0)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["address"],
            message: "Address or linked nodes required",
          });
        }
      })
  )
);
