// import {
//   Alert,
//   AlertIcon,
//   Box,
//   chakra,
//   Flex,
//   IconButton,
//   ModalBody,
//   Spinner,
//   Table,
//   Text,
//   Tbody,
//   Td,
//   Th,
//   Thead,
//   Tooltip,
//   Tr,
// } from "@chakra-ui/react";

// import { TrashIcon } from "@heroicons/react/24/outline";
// import dayjs from "dayjs";
// import { useTranslation } from "react-i18next";
// import { User, UserDevice } from "types/User";

// const DeleteDeviceIcon = chakra(TrashIcon, {
//   baseStyle: {
//     w: 4,
//     h: 4,
//   },
// });

// interface DeviceModalProps {
//   devicesError: string | null;
//   devicesLoading: boolean;
//   devices: UserDevice[];
//   deletingDeviceId: number | null;
//   editingUser: User | null | undefined;
//   setDeletingDeviceId: (id: number | null) => void;
//   setDevicesError: (error: string | null) => void;
//   setDevices: (
//     devices: UserDevice[] | ((prev: UserDevice[]) => UserDevice[])
//   ) => void;
//   toast: any;
// }

// export const DevicesModal = ({
//   devicesError,
//   devicesLoading,
//   devices,
//   deletingDeviceId,
//   editingUser,
//   setDeletingDeviceId,
//   setDevicesError,
//   setDevices,
//   toast,
// }: DeviceModalProps) => {
//   const { t } = useTranslation();

//   const deleteDevice = async (deviceId: number) => {
//     if (!editingUser) return;

//     setDeletingDeviceId(deviceId);
//     setDevicesError(null);
//     try {
//       await fetch(`/user/${editingUser.username}/devices/${deviceId}`, {
//         method: "DELETE",
//       });
//       setDevices((prev) => prev.filter((device) => device.id !== deviceId));
//       toast({
//         title: t("userDialog.deviceDeleted"),
//         status: "success",
//         isClosable: true,
//         position: "top",
//         duration: 3000,
//       });
//     } catch (err: any) {
//       setDevicesError(
//         err?.response?._data?.detail || t("userDialog.deviceDeleteError")
//       );
//     } finally {
//       setDeletingDeviceId(null);
//     }
//   };

//   return (
//     <ModalBody overflowX="auto">
//       {devicesError && (
//         <Alert status="error" mb="3">
//           <AlertIcon />
//           {devicesError}
//         </Alert>
//       )}
//       {devicesLoading ? (
//         <Flex justifyContent="center" py="6">
//           <Spinner />
//         </Flex>
//       ) : devices.length ? (
//         <Box w="max-content" maxW="full" overflowX="auto">
//           <Table
//             size="sm"
//             w="auto"
//             sx={{
//               tableLayout: "auto",
//               th: { whiteSpace: "nowrap", px: 2 },
//               td: {
//                 whiteSpace: "nowrap",
//                 px: 2,
//                 verticalAlign: "top",
//               },
//             }}
//           >
//             <Thead>
//               <Tr>
//                 <Th>HWID</Th>
//                 <Th>{t("userDialog.deviceOs")}</Th>
//                 <Th>{t("userDialog.deviceVerOs")}</Th>
//                 <Th>{t("userDialog.deviceModel")}</Th>
//                 <Th>User-Agent</Th>
//                 <Th>{t("userDialog.deviceFirstSeen")}</Th>
//                 <Th>{t("userDialog.deviceLastSeen")}</Th>
//                 <Th>Status</Th>
//                 <Th w="72px" textAlign="center" />
//               </Tr>
//             </Thead>
//             <Tbody>
//               {devices.map((device) => (
//                 <Tr key={device.id}>
//                   <Td>{device.hwid}</Td>
//                   <Td>{device.device_os || "-"}</Td>
//                   <Td>{device.ver_os || "-"}</Td>
//                   <Td>{device.device_model || "-"}</Td>
//                   <Td>{device.user_agent || "-"}</Td>
//                   <Td>
//                     {device.first_seen
//                       ? dayjs(device.first_seen).format("YYYY-MM-DD HH:mm")
//                       : "-"}
//                   </Td>
//                   <Td>
//                     {device.last_seen
//                       ? dayjs(device.last_seen).format("YYYY-MM-DD HH:mm")
//                       : "-"}
//                   </Td>
//                   <Td>
//                     <Text
//                       color={
//                         (device.status || "active").toLowerCase() === "active"
//                           ? "green.500"
//                           : (device.status || "").toLowerCase() === "revoked"
//                           ? "red.500"
//                           : "gray.500"
//                       }
//                       fontWeight="medium"
//                     >
//                       {device.status || "active"}
//                     </Text>
//                   </Td>
//                   <Td textAlign="center">
//                     <Tooltip label={t("delete")} placement="top">
//                       <IconButton
//                         aria-label={t("delete")}
//                         size="xs"
//                         variant="ghost"
//                         colorScheme="red"
//                         icon={<DeleteDeviceIcon />}
//                         isLoading={deletingDeviceId === device.id}
//                         onClick={() => deleteDevice(device.id)}
//                       />
//                     </Tooltip>
//                   </Td>
//                 </Tr>
//               ))}
//             </Tbody>
//           </Table>
//         </Box>
//       ) : (
//         <Text color="gray.500">{t("userDialog.devicesEmpty")}</Text>
//       )}
//     </ModalBody>
//   );
// };

// закрепленная кнопка удаления, если хотим оставить скролл
// import {
//   Alert,
//   AlertIcon,
//   Box,
//   chakra,
//   Flex,
//   IconButton,
//   ModalBody,
//   Spinner,
//   Table,
//   Text,
//   Tbody,
//   Td,
//   Th,
//   Thead,
//   Tooltip,
//   Tr,
// } from "@chakra-ui/react";

// import { TrashIcon } from "@heroicons/react/24/outline";
// import dayjs from "dayjs";
// import { useTranslation } from "react-i18next";
// import { User, UserDevice } from "types/User";

// const DeleteDeviceIcon = chakra(TrashIcon, {
//   baseStyle: {
//     w: 4,
//     h: 4,
//   },
// });

// interface DeviceModalProps {
//   devicesError: string | null;
//   devicesLoading: boolean;
//   devices: UserDevice[];
//   deletingDeviceId: number | null;
//   editingUser: User | null | undefined;
//   setDeletingDeviceId: (id: number | null) => void;
//   setDevicesError: (error: string | null) => void;
//   setDevices: (
//     devices: UserDevice[] | ((prev: UserDevice[]) => UserDevice[])
//   ) => void;
//   toast: any;
// }

// export const DevicesModal = ({
//   devicesError,
//   devicesLoading,
//   devices,
//   deletingDeviceId,
//   editingUser,
//   setDeletingDeviceId,
//   setDevicesError,
//   setDevices,
//   toast,
// }: DeviceModalProps) => {
//   const { t } = useTranslation();

//   const deleteDevice = async (deviceId: number) => {
//     if (!editingUser) return;

//     setDeletingDeviceId(deviceId);
//     setDevicesError(null);
//     try {
//       await fetch(`/user/${editingUser.username}/devices/${deviceId}`, {
//         method: "DELETE",
//       });
//       setDevices((prev) => prev.filter((device) => device.id !== deviceId));
//       toast({
//         title: t("userDialog.deviceDeleted"),
//         status: "success",
//         isClosable: true,
//         position: "top",
//         duration: 3000,
//       });
//     } catch (err: any) {
//       setDevicesError(
//         err?.response?._data?.detail || t("userDialog.deviceDeleteError")
//       );
//     } finally {
//       setDeletingDeviceId(null);
//     }
//   };

//   return (
//     <ModalBody overflow="auto" p={0}>
//       {devicesError && (
//         <Alert status="error" m={3}>
//           <AlertIcon />
//           {devicesError}
//         </Alert>
//       )}
//       {devicesLoading ? (
//         <Flex justifyContent="center" py="6">
//           <Spinner />
//         </Flex>
//       ) : devices.length ? (
//         <Box p={4}>
//           <Box overflowX="auto" maxH="60vh">
//             <Table
//               size="sm"
//               sx={{
//                 tableLayout: "auto",
//                 th: {
//                   whiteSpace: "nowrap",
//                   px: 2,
//                   position: "sticky",
//                   top: 0,
//                   bg: "gray.100",
//                   _dark: { bg: "gray.600" },
//                   zIndex: 1,
//                 },
//                 td: {
//                   whiteSpace: "nowrap",
//                   px: 2,
//                   verticalAlign: "top",
//                   maxW: "150px",
//                   overflow: "hidden",
//                   textOverflow: "ellipsis",
//                 },
//               }}
//             >
//               <Thead>
//                 <Tr>
//                   <Th minW="80px">HWID</Th>
//                   <Th minW="80px">{t("userDialog.deviceOs")}</Th>
//                   <Th minW="80px">{t("userDialog.deviceVerOs")}</Th>
//                   <Th minW="80px">{t("userDialog.deviceModel")}</Th>
//                   <Th minW="100px">User-Agent</Th>
//                   <Th minW="120px">{t("userDialog.deviceFirstSeen")}</Th>
//                   <Th minW="120px">{t("userDialog.deviceLastSeen")}</Th>
//                   <Th minW="80px">Status</Th>
//                   <Th
//                     w="72px"
//                     textAlign="center"
//                     position="sticky"
//                     right={0}
//                     bg="white"
//                     _dark={{ bg: "gray.800" }}
//                   >
//                     <Text>Actions</Text>
//                   </Th>
//                 </Tr>
//               </Thead>
//               <Tbody className="px-6 py-2">
//                 {devices.map((device) => (
//                   <Tr key={device.id}>
//                     <Td maxW="100px" overflow="hidden" textOverflow="ellipsis">
//                       {device.hwid}
//                     </Td>
//                     <Td>{device.device_os || "-"}</Td>
//                     <Td>{device.ver_os || "-"}</Td>
//                     <Td>{device.device_model || "-"}</Td>
//                     <Td maxW="120px" overflow="hidden" textOverflow="ellipsis">
//                       {device.user_agent || "-"}
//                     </Td>
//                     <Td>
//                       {device.first_seen
//                         ? dayjs(device.first_seen).format("YYYY-MM-DD HH:mm")
//                         : "-"}
//                     </Td>
//                     <Td>
//                       {device.last_seen
//                         ? dayjs(device.last_seen).format("YYYY-MM-DD HH:mm")
//                         : "-"}
//                     </Td>
//                     <Td>
//                       <Text
//                         color={
//                           (device.status || "active").toLowerCase() === "active"
//                             ? "green.500"
//                             : (device.status || "").toLowerCase() === "revoked"
//                             ? "red.500"
//                             : "gray.500"
//                         }
//                         fontWeight="medium"
//                       >
//                         {device.status || "active"}
//                       </Text>
//                     </Td>
//                     <Td
//                       textAlign="center"
//                       position="sticky"
//                       right={0}
//                       bg="white"
//                       _dark={{ bg: "gray.800" }}
//                       boxShadow="-4px 0 8px rgba(0,0,0,0.05)"
//                     >
//                       <Tooltip label={t("delete")} placement="top">
//                         <IconButton
//                           aria-label={t("delete")}
//                           size="xs"
//                           variant="ghost"
//                           colorScheme="red"
//                           icon={<DeleteDeviceIcon />}
//                           isLoading={deletingDeviceId === device.id}
//                           onClick={() => deleteDevice(device.id)}
//                         />
//                       </Tooltip>
//                     </Td>
//                   </Tr>
//                 ))}
//               </Tbody>
//             </Table>
//           </Box>
//         </Box>
//       ) : (
//         <Flex
//           direction="column"
//           align="center"
//           justify="center"
//           py={12}
//           px={6}
//           minH="200px"
//         >
//           <Text color="gray.500" fontSize="md" textAlign="center">
//             {t("userDialog.devicesEmpty")}
//           </Text>
//         </Flex>
//       )}
//     </ModalBody>
//   );
// };

import {
  Alert,
  AlertIcon,
  Box,
  chakra,
  Flex,
  IconButton,
  ModalBody,
  Spinner,
  Table,
  Text,
  Tbody,
  Td,
  Th,
  Thead,
  Tooltip,
  Tr,
} from "@chakra-ui/react";

import { TrashIcon } from "@heroicons/react/24/outline";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { User, UserDevice } from "types/User";

const DeleteDeviceIcon = chakra(TrashIcon, {
  baseStyle: {
    w: 4,
    h: 4,
  },
});

interface DeviceModalProps {
  devicesError: string | null;
  devicesLoading: boolean;
  devices: UserDevice[];
  deletingDeviceId: number | null;
  editingUser: User | null | undefined;
  setDeletingDeviceId: (id: number | null) => void;
  setDevicesError: (error: string | null) => void;
  setDevices: (
    devices: UserDevice[] | ((prev: UserDevice[]) => UserDevice[])
  ) => void;
  toast: any;
}

export const DevicesModal = ({
  devicesError,
  devicesLoading,
  devices,
  deletingDeviceId,
  editingUser,
  setDeletingDeviceId,
  setDevicesError,
  setDevices,
  toast,
}: DeviceModalProps) => {
  const { t } = useTranslation();

  const deleteDevice = async (deviceId: number) => {
    if (!editingUser) return;

    setDeletingDeviceId(deviceId);
    setDevicesError(null);
    try {
      await fetch(`/user/${editingUser.username}/devices/${deviceId}`, {
        method: "DELETE",
      });
      setDevices((prev) => prev.filter((device) => device.id !== deviceId));
      toast({
        title: t("userDialog.deviceDeleted"),
        status: "success",
        isClosable: true,
        position: "top",
        duration: 3000,
      });
    } catch (err: any) {
      setDevicesError(
        err?.response?._data?.detail || t("userDialog.deviceDeleteError")
      );
    } finally {
      setDeletingDeviceId(null);
    }
  };

  return (
    <ModalBody overflow="auto" p={0}>
      {devicesError && (
        <Alert status="error" m={3}>
          <AlertIcon />
          {devicesError}
        </Alert>
      )}
      {devicesLoading ? (
        <Flex justifyContent="center" py="6">
          <Spinner />
        </Flex>
      ) : devices.length ? (
        <Box p={4}>
          <Box overflowX="auto" maxH="60vh">
            <Table
              size="sm"
              sx={{
                tableLayout: "auto",
                th: {
                  whiteSpace: "nowrap",
                  px: 2,
                  position: "sticky",
                  top: 0,
                  bg: "gray.100",
                  _dark: { bg: "gray.600" },
                  zIndex: 1,
                },
                td: {
                  whiteSpace: "nowrap",
                  px: 2,
                  verticalAlign: "top",
                  maxW: "150px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                },
              }}
            >
              <Thead>
                <Tr>
                  <Th minW="80px">HWID</Th>
                  <Th minW="80px">{t("userDialog.deviceOs")}</Th>
                  <Th minW="80px">{t("userDialog.deviceVerOs")}</Th>
                  <Th minW="80px">{t("userDialog.deviceModel")}</Th>
                  <Th minW="100px">User-Agent</Th>
                  <Th minW="120px">{t("userDialog.deviceFirstSeen")}</Th>
                  <Th minW="120px">{t("userDialog.deviceLastSeen")}</Th>
                  <Th minW="80px">Status</Th>
                  <Th
                    w="72px"
                    textAlign="center"
                    position="sticky"
                    right={0}
                    bg="white"
                    _dark={{ bg: "gray.800" }}
                  >
                    <Text>Actions</Text>
                  </Th>
                </Tr>
              </Thead>
              <Tbody className="px-6 py-2">
                {devices.map((device) => (
                  <Tr key={device.id}>
                    <Td maxW="100px" overflow="hidden" textOverflow="ellipsis">
                      {device.hwid}
                    </Td>
                    <Td>{device.device_os || "-"}</Td>
                    <Td>{device.ver_os || "-"}</Td>
                    <Td>{device.device_model || "-"}</Td>
                    <Td maxW="120px" overflow="hidden" textOverflow="ellipsis">
                      {device.user_agent || "-"}
                    </Td>
                    <Td>
                      {device.first_seen
                        ? dayjs(device.first_seen).format("YYYY-MM-DD HH:mm")
                        : "-"}
                    </Td>
                    <Td>
                      {device.last_seen
                        ? dayjs(device.last_seen).format("YYYY-MM-DD HH:mm")
                        : "-"}
                    </Td>
                    <Td>
                      <Text
                        color={
                          (device.status || "active").toLowerCase() === "active"
                            ? "green.500"
                            : (device.status || "").toLowerCase() === "revoked"
                            ? "red.500"
                            : "gray.500"
                        }
                        fontWeight="medium"
                      >
                        {device.status || "active"}
                      </Text>
                    </Td>
                    <Td
                      textAlign="center"
                      position="sticky"
                      right={0}
                      bg="white"
                      _dark={{ bg: "gray.800" }}
                      boxShadow="-4px 0 8px rgba(0,0,0,0.05)"
                    >
                      <Tooltip label={t("delete")} placement="top">
                        <IconButton
                          aria-label={t("delete")}
                          size="xs"
                          variant="ghost"
                          colorScheme="red"
                          icon={<DeleteDeviceIcon />}
                          isLoading={deletingDeviceId === device.id}
                          onClick={() => deleteDevice(device.id)}
                        />
                      </Tooltip>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </Box>
      ) : (
        <Flex
          direction="column"
          align="center"
          justify="center"
          py={12}
          px={6}
          minH="200px"
        >
          <Text color="gray.500" fontSize="md" textAlign="center">
            {t("userDialog.devicesEmpty")}
          </Text>
        </Flex>
      )}
    </ModalBody>
  );
};
