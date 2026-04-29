import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { oktaAuth } from "./authConfig";


// ⚠️ TEMPORARY MOCK FOR AWS-AMPLIFY/AUTH
const fetchAuthSession = async () => ({
  tokens: { accessToken: "MOCK_ACCESS_TOKEN" },
  userSub: "cog-alice",
});

const getCurrentUser = async () => ({
  username: "mock_user",
  userId: "MOCK_USER_ID",
});
// ------------------------------------------

// --- INTERFACES ---

export interface Project {
  id: number;
  name: string;
  description?: string;
  startDate?: string;
  endDate?: string;
}

export enum Priority {
  Urgent = "Urgent",
  High = "High",
  Medium = "Medium",
  Low = "Low",
  Backlog = "Backlog",
}

export enum Status {
  ToDo = "To Do",
  WorkInProgress = "Work In Progress",
  UnderReview = "Under Review",
  Completed = "Completed",
}

export interface User {
  userId?: number;
  username: string;
  email: string;
  profilePictureUrl?: string;
  cognitoId?: string;
  teamId?: number;
}

export interface Attachment {
  id: number;
  fileURL: string;
  fileName: string;
  taskId: number;
  uploadedById: number;
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  status?: Status;
  priority?: Priority;
  tags?: string;
  startDate?: string;
  dueDate?: string;
  points?: number;
  projectId: number;
  authorUserId?: number;
  assignedUserId?: number;
  author?: User;
  assignee?: User;
  comments?: any[]; 
  attachments?: Attachment[];
}

export interface SearchResults {
  tasks?: Task[];
  projects?: Project[];
  users?: User[];
}

export interface Team {
  teamId: number;
  teamName: string;
  productOwnerUserId?: number;
  projectManagerUserId?: number;
}

export interface AuthUserResponse {
    user: { username: string; userId: string; };
    userSub: string;
    userDetails: User;
}

export interface UploadResponse {
  message: string;
  count: number;
}

export interface QcSummaryResult {
    id: number;
    description: string;
    action: string;
    status: string;
    total_issues_flagged: number;
}

export interface QcRunResponse {
    status: string;
    message: string;
    download_url: string;
    summaries: QcSummaryResult[];
}

// 💡 NEW INTERFACES FOR EARLY WARNING DASHBOARD
export interface BsaRecord {
  "TV Channel": string;
  "Market": string;
  "Channel ID": string;
  "Critical Channel": string;
  "Final Status": string;
  [key: string]: any; // Dynamic date columns
}

export interface TrendRecord {
  Date: string;
  Scheduled: number;
  "Processing Gaps": number;
  "No Schedule": number;
}

export interface MandatoryRecord {
  Channel: string;
  "Found in BSA?": string;
  Status: string;
}

export interface RoscoRecord {
  Channel: string;
  Market: string;
  "IN AURA": string;
  "IN BSA": string;
  "Final Status": string;
  [key: string]: any;
}

export interface EarlyWarningResponse {
  bsa_view: BsaRecord[];
  trend_stats: TrendRecord[];
  mandatory_audit: MandatoryRecord[];
  rosco_view: RoscoRecord[];
  date_columns: string[];
}

export interface DeliveryRecord {
  tracking_id: string;
  delivery_uid: string;
  client_account: string;
  description_text: string;
  owner_fte: string;
  office_location: string;
  sport_category: string;
  target_date: string;
  delivery_status: string;
  delay_severity: number;
  is_backlog: number;
  delivery_metrics: {
    [key: string]: {
      Total_Evaluated: number;
      Passed: number;
      Failed: number;
    };
  };
  [key: string]: any;
}

// --- API DEFINITION ---

export const api = createApi({
  baseQuery: fetchBaseQuery({
    baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
    timeout : 600000,
    prepareHeaders: async (headers) => {
      if (oktaAuth) {
        const token = oktaAuth.getAccessToken();
        if (token) {
          headers.set("Authorization", `Bearer ${token}`);
        }
      }
      return headers;
    },
  }),
  reducerPath: "api",
  tagTypes: ["Projects", "Tasks", "Users", "Teams", "EPLFixtures", "EPLStandings", "EPLChecks", "QcResults","DeliveryAnalytics"],
  endpoints: (build) => ({
    getAuthUser: build.query<any, void>({
      queryFn: async (_, _queryApi, _extraoptions, fetchWithBQ) => {
        try {
          // 🚨 LOCAL DEV SWITCH: Feed Redux a fake user so it ignores Okta
          const isLocalDev = typeof window !== 'undefined' && window.location.hostname === 'localhost';
          if (isLocalDev) {
            return { 
              data: { 
                user: { username: "Local Admin", userId: "00u23vc7vi2VW8tBj0h8" }, 
                userSub: "00u23vc7vi2VW8tBj0h8", 
                userDetails: { username: "Local Admin", profilePictureUrl: "i1.jpg", teamId: 1 } 
              } 
            };
          }

          // --- NORMAL PRODUCTION OKTA FETCH ---
          if (!oktaAuth) throw new Error("Okta Auth not initialized");
          const user = await oktaAuth.getUser();
          if (!user) throw new Error("No user found in Okta session");

          const userSub = user.sub; 
          const authUser = {
            username: user.preferred_username || user.name || "Unknown User",
            userId: userSub,
          };

          const userDetailsResponse = await fetchWithBQ(`dashboard/users/${userSub}`);
          const userDetails = userDetailsResponse.data;

          return { data: { user: authUser, userSub, userDetails } };
        } catch (error: any) {
          return { error: error.message || "Could not fetch user data" };
        }
      },
      providesTags: ["Users"], 
    }),
    
    getProjects: build.query<Project[], void>({
      query: () => "/dashboard/projects",
      providesTags: ["Projects"],
    }),
    
    createProject: build.mutation<Project, Partial<Project>>({
      query: (project) => ({
        url: "/dashboard/projects",
        method: "POST",
        body: project,
      }),
      invalidatesTags: ["Projects"],
    }),
    
    getTasks: build.query<Task[], { projectId: number }>({
      query: ({ projectId }) => `/dashboard/tasks/?projectId=${projectId}`,
      providesTags: (result) =>
        result
          ? result.map(({ id }) => ({ type: "Tasks" as const, id }))
          : [{ type: "Tasks" as const }],
    }),
    
    getTasksByUser: build.query<Task[], number>({
      query: (userId) => `/dashboard/tasks/user/${userId}`,
      providesTags: (result, error, userId) =>
        result
          ? result.map(({ id }) => ({ type: "Tasks", id }))
          : [{ type: "Tasks", id: userId }],
    }),
    
    createTask: build.mutation<Task, Partial<Task>>({
      query: (task) => ({
        url: "/dashboard/tasks",
        method: "POST",
        body: task,
      }),
      invalidatesTags: ["Tasks"],
    }),
    
    updateTaskStatus: build.mutation<Task, { taskId: number; status: string }>({
      query: ({ taskId, status }) => ({
        url: `/dashboard/tasks/${taskId}/status`,
        method: "PATCH",
        body: { status },
      }),
      invalidatesTags: (result, error, { taskId }) => [
        { type: "Tasks", id: taskId },
      ],
    }),
    
    getUsers: build.query<User[], void>({
      query: () => "/dashboard/users/",
      providesTags: ["Users"],
    }),
    
    getTeams: build.query<Team[], void>({
      query: () => "/dashboard/teams",
      providesTags: ["Teams"],
    }),
    
    search: build.query<SearchResults, string>({
      query: (query) => `/dashboard/search?query=${query}`,
    }),
    
    runQcChecks: build.mutation<QcRunResponse, FormData>({
      query: (formData) => ({
        url: "qc/run_qc", 
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["QcResults"], 
    }),

    runQcChecks1: build.mutation<QcRunResponse, FormData>({
      query: (formData) => ({
        url: "qc/run_qc1", 
        method: "POST",
        body: formData,
        responseHandler: (response) => response.blob(),
      }),
      invalidatesTags: ["QcResults"], 
    }),

    runMarketChecks: build.mutation<QcRunResponse, FormData>({
        query: (formData) => ({
            url: "qc/market_check_and_process",
            method: "POST",
            body: formData,
        }),
        invalidatesTags: ["QcResults"], 
    }),

    // 💡 NEW MUTATION FOR EARLY WARNING DASHBOARD
    runEarlyWarningAnalysis: build.mutation<EarlyWarningResponse, FormData>({
      query: (formData) => ({
        url: "qc/early-warning", // Ensure this matches your FastAPI router path
        method: "POST",
        body: formData,
      }),
    }),

    runEarlyWarningAnalysis1: build.mutation<EarlyWarningResponse, FormData>({
      query: (formData) => ({
        url: "qc/early-warning1", // Ensure this matches your FastAPI router path
        method: "POST",
        body: formData,
      }),
    }),

    runMmBsaQc: build.mutation<Blob, FormData>({
      query: (formData) => ({
        url: "qc/run-mm-bsa-qc", // Make sure this matches your FastAPI router prefix + endpoint
        method: "POST",
        body: formData,
        responseHandler: (response) => response.blob(),
      }),
    }),

    downloadFixtureTemplate: build.query<Blob, void>({
      query: () => ({
        url: "qc/download-fixture-template", // Ensure this matches your router prefix
        method: "GET",
        responseHandler: (response) => response.blob(),
      }),
    }),

    getQcHistory: build.query<any[], void>({
      query: () => "/qc/history",
      // Optional: Add a providesTags if you want to auto-refresh this when a new test runs
      // providesTags: ["QcHistory"], 
    }),

    getDeliveryDashboard: build.query<DeliveryRecord[], void>({
      query: () => "qc/delivery-analytics",
      providesTags: ["DeliveryAnalytics"],
    }),


    
    uploadFile: build.mutation<UploadResponse, FormData>({
        query: (formData) => ({
            url: "upload/data",
            method: "POST",
            body: formData,
        }),
    }),

    downloadWeeklyQcReport: build.query<Blob, { start_date?: string; end_date?: string }>({
      query: (params) => ({
        url: "qc/history/weekly-export",
        method: "GET",
        params: params, // RTK Query automatically turns this into ?start_date=X&end_date=Y
        responseHandler: (response) => response.blob(),
      }),
    }),


  }),
});

// --- EXPORT HOOKS ---

export const {
  useGetProjectsQuery,
  useCreateProjectMutation,
  useGetTasksQuery,
  useCreateTaskMutation,
  useUpdateTaskStatusMutation,
  useSearchQuery,
  useGetUsersQuery,
  useGetTeamsQuery,
  useGetTasksByUserQuery,
  useGetAuthUserQuery,
  useRunQcChecksMutation,
  useRunQcChecks1Mutation,
  useRunMarketChecksMutation,
  useUploadFileMutation,
  // 💡 Export the new hook
  useRunEarlyWarningAnalysisMutation,   
  useRunEarlyWarningAnalysis1Mutation,
  useRunMmBsaQcMutation, 
  useLazyDownloadFixtureTemplateQuery,
  //history
  useGetQcHistoryQuery,
  useGetDeliveryDashboardQuery,

  useLazyDownloadWeeklyQcReportQuery,
} = api;

// import { createApi, fetchBaseQuery, BaseQueryApi } from "@reduxjs/toolkit/query/react";

// // ⚠️ TEMPORARY MOCK FOR AWS-AMPLIFY/AUTH
// // These mock functions replace the real imports for temporary development.
// const fetchAuthSession = async () => ({
//   tokens: { accessToken: "MOCK_ACCESS_TOKEN" }, // Provide a dummy token
//   userSub: "cog-alice",
// });

// const getCurrentUser = async () => ({
//   username: "mock_user",
//   userId: "MOCK_USER_ID",
// });
// // ------------------------------------------

// // --- INTERFACES ---

// export interface Project {
//   id: number;
//   name: string;
//   description?: string;
//   startDate?: string;
//   endDate?: string;
// }

// export enum Priority {
//   Urgent = "Urgent",
//   High = "High",
//   Medium = "Medium",
//   Low = "Low",
//   Backlog = "Backlog",
// }

// export enum Status {
//   ToDo = "To Do",
//   WorkInProgress = "Work In Progress",
//   UnderReview = "Under Review",
//   Completed = "Completed",
// }

// export interface User {
//   userId?: number;
//   username: string;
//   email: string;
//   profilePictureUrl?: string;
//   cognitoId?: string;
//   teamId?: number;
// }

// export interface Attachment {
//   id: number;
//   fileURL: string;
//   fileName: string;
//   taskId: number;
//   uploadedById: number;
// }

// export interface Task {
//   id: number;
//   title: string;
//   description?: string;
//   status?: Status;
//   priority?: Priority;
//   tags?: string;
//   startDate?: string;
//   dueDate?: string;
//   points?: number;
//   projectId: number;
//   authorUserId?: number;
//   assignedUserId?: number;

//   author?: User;
//   assignee?: User;
//   // NOTE: Assuming Comment interface is defined elsewhere or not strictly needed here
//   comments?: any[]; 
//   attachments?: Attachment[];
// }

// export interface SearchResults {
//   tasks?: Task[];
//   projects?: Project[];
//   users?: User[];
// }

// export interface Team {
//   teamId: number;
//   teamName: string;
//   productOwnerUserId?: number;
//   projectManagerUserId?: number;
// }

// export interface AuthUserResponse {
//     user: { username: string; userId: string; }; // Based on mock/getCurrentUser
//     userSub: string;
//     userDetails: User;
// }

// // 💡 NEW INTERFACES FOR QC PROCESS
// export interface UploadResponse {
//   message: string;
//   count: number;
// }

// export interface QcSummaryResult {
//     id: number;
//     description: string;
//     action: string;
//     status: string;
//     total_issues_flagged: number;
//     // Add any other fields your backend returns in the summary
// }

// export interface QcRunResponse {
//     status: string;
//     message: string;
//     download_url: string;
//     summaries: QcSummaryResult[]; // This is the array
// }

// // --- API DEFINITION ---

// export const api = createApi({
//   baseQuery: fetchBaseQuery({
//     baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
//     timeout : 600000,
//     prepareHeaders: async (headers) => {
//       // Uses the mock fetchAuthSession for the Bearer token
//       const session = await fetchAuthSession();
//       const { accessToken } = session.tokens ?? {};
//       if (accessToken) {
//         headers.set("Authorization", `Bearer ${accessToken}`);
//       }
//       return headers;
//     },
//   }),
//   reducerPath: "api",
//   // 💡 Updated tagTypes to include QcResults
//   tagTypes: ["Projects", "Tasks", "Users", "Teams", "EPLFixtures", "EPLStandings", "EPLChecks", "QcResults"],
//   endpoints: (build) => ({
//     getAuthUser: build.query<AuthUserResponse, void>({
//       queryFn: async (_, _queryApi, _extraoptions, fetchWithBQ) => {
//         try {
//           const user = await getCurrentUser();
//           const session = await fetchAuthSession();
          
//           if (!session) throw new Error("No session found");
//           const { userSub } = session;

//           // fetchWithBQ will use the mock token in the header
//           const userDetailsResponse = await fetchWithBQ(`dashboard/users/${userSub}`);
//           const userDetails = userDetailsResponse.data as User;

//           return { data: { user, userSub, userDetails } };
//         } catch (error: any) {
//           return { error: error.message || "Could not fetch user data" };
//         }
//       },
//       providesTags: ["Users"], 
//     }),
    
//     getProjects: build.query<Project[], void>({
//       query: () => "/dashboard/projects/",
//       providesTags: ["Projects"],
//     }),
    
//     createProject: build.mutation<Project, Partial<Project>>({
//       query: (project) => ({
//         url: "/dashboard/projects",
//         method: "POST",
//         body: project,
//       }),
//       invalidatesTags: ["Projects"],
//     }),
    
//     getTasks: build.query<Task[], { projectId: number }>({
//       query: ({ projectId }) => `/dashboard/tasks?projectId=${projectId}`,
//       providesTags: (result) =>
//         result
//           ? result.map(({ id }) => ({ type: "Tasks" as const, id }))
//           : [{ type: "Tasks" as const }],
//     }),
    
//     getTasksByUser: build.query<Task[], number>({
//       query: (userId) => `/dashboard/tasks/user/${userId}`,
//       providesTags: (result, error, userId) =>
//         result
//           ? result.map(({ id }) => ({ type: "Tasks", id }))
//           : [{ type: "Tasks", id: userId }],
//     }),
    
//     createTask: build.mutation<Task, Partial<Task>>({
//       query: (task) => ({
//         url: "/dashboard/tasks",
//         method: "POST",
//         body: task,
//       }),
//       invalidatesTags: ["Tasks"],
//     }),
    
//     updateTaskStatus: build.mutation<Task, { taskId: number; status: string }>({
//       query: ({ taskId, status }) => ({
//         url: `/dashboard/tasks/${taskId}/status`,
//         method: "PATCH",
//         body: { status },
//       }),
//       invalidatesTags: (result, error, { taskId }) => [
//         { type: "Tasks", id: taskId },
//       ],
//     }),
    
//     getUsers: build.query<User[], void>({
//       query: () => "/dashboard/users",
//       providesTags: ["Users"],
//     }),
    
//     getTeams: build.query<Team[], void>({
//       query: () => "/dashboard/teams",
//       providesTags: ["Teams"],
//     }),
    
//     search: build.query<SearchResults, string>({
//       query: (query) => `/dashboard/search?query=${query}`,
//     }),
    
//     // 💡 NEW MUTATION: runQcChecks
//     runQcChecks: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         // Assuming your backend uses this path for the QC pipeline
//         url: "qc/run_qc", 
//         method: "POST",
//         body: formData,
//       }),
//       // Invalidate the QcResults tag to force a potential refetch of any Qc-related queries
//       invalidatesTags: ["QcResults"], 
//     }),

//     // runUsaRateCalculation: build.mutation<Blob, FormData>({
//     //   query: (formData) => ({
//     //     url: "qc/calculate_usa_final_audit", 
//     //     method: "POST",
//     //     body: formData,
//     //     responseHandler: (response) => response.blob(),
//     //   }),
//     //   invalidatesTags: (result, error, arg) => ["QcResults"],
//     // }),

//     runQcChecks1: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         url: "qc/run_qc1", 
//         method: "POST",
//         body: formData,
//         responseHandler: (response) => response.blob(),
//       }),
//       invalidatesTags: ["QcResults"], 
//     }),

//     runMarketChecks: build.mutation<QcRunResponse, FormData>({
//         query: (formData) => ({
//             url: "qc/market_check_and_process", // The target URL
//             method: "POST",
//             body: formData,
//         }),
//         invalidatesTags: ["QcResults"], 
//     }),
    
//     // 💡 Optional: Keep a generic uploadFile if needed elsewhere
//     uploadFile: build.mutation<UploadResponse, FormData>({
//         query: (formData) => ({
//             url: "upload/data",
//             method: "POST",
//             body: formData,
//         }),
//     }),
//   }),
// });

// // --- EXPORT HOOKS ---

// export const {
//   // useRunUsaRateCalculationMutation, // 💡 NEW EXPORT
//   useGetProjectsQuery,
//   useCreateProjectMutation,
//   useGetTasksQuery,
//   useCreateTaskMutation,
//   useUpdateTaskStatusMutation,
//   useSearchQuery,
//   useGetUsersQuery,
//   useGetTeamsQuery,
//   useGetTasksByUserQuery,
//   useGetAuthUserQuery,
//   // 💡 NEW EXPORTS
//   useRunQcChecksMutation,
//   useRunQcChecks1Mutation,
//   useRunMarketChecksMutation, // 💡 NEW EXPORT
//   useUploadFileMutation,
// } = api;



  // import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
  // import { oktaAuth } from "./authConfig"; // This should contain your ClientID and Nielsen Issuer

  // // --- INTERFACES ---

  // export interface Project {
  //   id: number;
  //   name: string;
  //   description?: string;
  //   startDate?: string;
  //   endDate?: string;
  // }

  // export enum Priority {
  //   Urgent = "Urgent",
  //   High = "High",
  //   Medium = "Medium",
  //   Low = "Low",
  //   Backlog = "Backlog",
  // }

  // export enum Status {
  //   ToDo = "To Do",
  //   WorkInProgress = "Work In Progress",
  //   UnderReview = "Under Review",
  //   Completed = "Completed",
  // }

  // export interface User {
  //   userId?: number;
  //   username: string;
  //   email: string;
  //   profilePictureUrl?: string;
  //   cognitoId?: string; // You might rename this to oktaId later
  //   teamId?: number;
  // }

  // export interface Attachment {
  //   id: number;
  //   fileURL: string;
  //   fileName: string;
  //   taskId: number;
  //   uploadedById: number;
  // }

  // export interface Task {
  //   id: number;
  //   title: string;
  //   description?: string;
  //   status?: Status;
  //   priority?: Priority;
  //   tags?: string;
  //   startDate?: string;
  //   dueDate?: string;
  //   points?: number;
  //   projectId: number;
  //   authorUserId?: number;
  //   assignedUserId?: number;
  //   author?: User;
  //   assignee?: User;
  //   comments?: any[]; 
  //   attachments?: Attachment[];
  // }

  // export interface SearchResults {
  //   tasks?: Task[];
  //   projects?: Project[];
  //   users?: User[];
  // }

  // export interface Team {
  //   teamId: number;
  //   teamName: string;
  //   productOwnerUserId?: number;
  //   projectManagerUserId?: number;
  // }

  // export interface AuthUserResponse {
  //     user: { username: string; userId: string; }; 
  //     userSub: string;
  //     userDetails: User;
  // }

  // export interface UploadResponse {
  //   message: string;
  //   count: number;
  // }

  // export interface QcSummaryResult {
  //     id: number;
  //     description: string;
  //     action: string;
  //     status: string;
  //     total_issues_flagged: number;
  // }

  // export interface QcRunResponse {
  //     status: string;
  //     message: string;
  //     download_url: string;
  //     summaries: QcSummaryResult[];
  // }

  // // --- API DEFINITION ---

  // export const api = createApi({
  //   baseQuery: fetchBaseQuery({
  //     baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  //     timeout: 600000,
  //     prepareHeaders: async (headers) => {
  //       // 💡 GUARD: oktaAuth is null on server, so we skip header setting there
  //       if (oktaAuth) {
  //         const accessToken = oktaAuth.getAccessToken();
  //         if (accessToken) {
  //           headers.set("Authorization", `Bearer ${accessToken}`);
  //         }
  //       }
  //       return headers;
  //     },
  //   }),
  //   reducerPath: "api",
  //   tagTypes: ["Projects", "Tasks", "Users", "Teams", "EPLFixtures", "EPLStandings", "EPLChecks", "QcResults"],
  //   endpoints: (build) => ({
  //     getAuthUser: build.query<AuthUserResponse, void>({
  //       queryFn: async (_, _queryApi, _extraoptions, fetchWithBQ) => {
  //         // 💡 GUARD: If on server or no oktaAuth, return early
  //         if (!oktaAuth) return { error: { status: 401, data: "Not authenticated (SSR)" } };

  //         try {
  //           const oktaUser = await oktaAuth.getUser();
  //           if (!oktaUser || !oktaUser.sub) {
  //             throw new Error("No active Okta session found");
  //           }

  //           const userSub = oktaUser.sub;
  //           const userDetailsResponse = await fetchWithBQ(`dashboard/users/${userSub}`);
            
  //           if (userDetailsResponse.error) {
  //             return { error: userDetailsResponse.error as any };
  //           }

  //           const userDetails = userDetailsResponse.data as User;

  //           return { 
  //             data: { 
  //               user: { 
  //                 username: oktaUser.preferred_username || oktaUser.name || "Nielsen User", 
  //                 userId: userSub 
  //               }, 
  //               userSub, 
  //               userDetails 
  //             } 
  //           };
  //         } catch (error: any) {
  //           return { error: error.message || "Could not fetch user data from Okta" };
  //         }
  //       },
  //       providesTags: ["Users"], 
  //     }),
      
  //     getProjects: build.query<Project[], void>({
  //       query: () => "/dashboard/projects/",
  //       providesTags: ["Projects"],
  //     }),
      
  //     createProject: build.mutation<Project, Partial<Project>>({
  //       query: (project) => ({
  //         url: "/dashboard/projects",
  //         method: "POST",
  //         body: project,
  //       }),
  //       invalidatesTags: ["Projects"],
  //     }),
      
  //     getTasks: build.query<Task[], { projectId: number }>({
  //       query: ({ projectId }) => `/dashboard/tasks?projectId=${projectId}`,
  //       providesTags: (result) =>
  //         result
  //           ? result.map(({ id }) => ({ type: "Tasks" as const, id }))
  //           : [{ type: "Tasks" as const }],
  //     }),
      
  //     getTasksByUser: build.query<Task[], number>({
  //       query: (userId) => `/dashboard/tasks/user/${userId}`,
  //       providesTags: (result, error, userId) =>
  //         result
  //           ? result.map(({ id }) => ({ type: "Tasks", id }))
  //           : [{ type: "Tasks", id: userId }],
  //     }),
      
  //     createTask: build.mutation<Task, Partial<Task>>({
  //       query: (task) => ({
  //         url: "/dashboard/tasks",
  //         method: "POST",
  //         body: task,
  //       }),
  //       invalidatesTags: ["Tasks"],
  //     }),
      
  //     updateTaskStatus: build.mutation<Task, { taskId: number; status: string }>({
  //       query: ({ taskId, status }) => ({
  //         url: `/dashboard/tasks/${taskId}/status`,
  //         method: "PATCH",
  //         body: { status },
  //       }),
  //       invalidatesTags: (result, error, { taskId }) => [
  //         { type: "Tasks", id: taskId },
  //       ],
  //     }),
      
  //     getUsers: build.query<User[], void>({
  //       query: () => "/dashboard/users",
  //       providesTags: ["Users"],
  //     }),
      
  //     getTeams: build.query<Team[], void>({
  //       query: () => "/dashboard/teams",
  //       providesTags: ["Teams"],
  //     }),
      
  //     search: build.query<SearchResults, string>({
  //       query: (query) => `/dashboard/search?query=${query}`,
  //     }),
      
  //     runQcChecks: build.mutation<QcRunResponse, FormData>({
  //       query: (formData) => ({
  //         url: "qc/run_qc", 
  //         method: "POST",
  //         body: formData,
  //       }),
  //       invalidatesTags: ["QcResults"], 
  //     }),

  //     runUsaRateCalculation: build.mutation<Blob, FormData>({
  //       query: (formData) => ({
  //         url: "qc/calculate_usa_final_audit", 
  //         method: "POST",
  //         body: formData,
  //         responseHandler: (response) => response.blob(),
  //       }),
  //       invalidatesTags: ["QcResults"],
  //     }),

  //     runQcChecks1: build.mutation<QcRunResponse, FormData>({
  //       query: (formData) => ({
  //         url: "qc/run_qc1", 
  //         method: "POST",
  //         body: formData,
  //         responseHandler: (response) => response.blob(),
  //       }),
  //       invalidatesTags: ["QcResults"], 
  //     }),

  //     runMarketChecks: build.mutation<QcRunResponse, FormData>({
  //         query: (formData) => ({
  //             url: "qc/market_check_and_process", 
  //             method: "POST",
  //             body: formData,
  //         }),
  //         invalidatesTags: ["QcResults"], 
  //     }),
      
  //     uploadFile: build.mutation<UploadResponse, FormData>({
  //         query: (formData) => ({
  //             url: "upload/data",
  //             method: "POST",
  //             body: formData,
  //         }),
  //     }),
  //   }),
  // });

  // // --- EXPORT HOOKS ---

  // export const {
  //   useRunUsaRateCalculationMutation,
  //   useGetProjectsQuery,
  //   useCreateProjectMutation,
  //   useGetTasksQuery,
  //   useCreateTaskMutation,
  //   useUpdateTaskStatusMutation,
  //   useSearchQuery,
  //   useGetUsersQuery,
  //   useGetTeamsQuery,
  //   useGetTasksByUserQuery,
  //   useGetAuthUserQuery,
  //   useRunQcChecksMutation,
  //   useRunQcChecks1Mutation,
  //   useRunMarketChecksMutation,
  //   useUploadFileMutation,
  // } = api;



























// import {
//   createApi,
//   fetchBaseQuery,
//   FetchBaseQueryError,
// } from "@reduxjs/toolkit/query/react";
// import type { BaseQueryApi } from "@reduxjs/toolkit/query";
// // import { oktaAuth } from "@/auth/okta"; // 👈 Okta client instance
// import { oktaAuth } from "@/auth/okta"

// /* -------------------------------------------------------------------------- */
// /*                               INTERFACES                                   */
// /* -------------------------------------------------------------------------- */



// export interface Project {
//   id: number;
//   name: string;
//   description?: string;
//   startDate?: string;
//   endDate?: string;
// }

// export enum Priority {
//   Urgent = "Urgent",
//   High = "High",
//   Medium = "Medium",
//   Low = "Low",
//   Backlog = "Backlog",
// }

// export enum Status {
//   ToDo = "To Do",
//   WorkInProgress = "Work In Progress",
//   UnderReview = "Under Review",
//   Completed = "Completed",
// }

// export interface User {
//   userId?: number;
//   username: string;
//   email: string;
//   profilePictureUrl?: string;
//   oktaId?: string;
//   teamId?: number;
// }

// export interface Attachment {
//   id: number;
//   fileURL: string;
//   fileName: string;
//   taskId: number;
//   uploadedById: number;
// }

// export interface Task {
//   id: number;
//   title: string;
//   description?: string;
//   status?: Status;
//   priority?: Priority;
//   tags?: string;
//   startDate?: string;
//   dueDate?: string;
//   points?: number;
//   projectId: number;
//   authorUserId?: number;
//   assignedUserId?: number;

//   author?: User;
//   assignee?: User;
//   comments?: any[];
//   attachments?: Attachment[];
// }

// export interface SearchResults {
//   tasks?: Task[];
//   projects?: Project[];
//   users?: User[];
// }

// export interface Team {
//   teamId: number;
//   teamName: string;
//   productOwnerUserId?: number;
//   projectManagerUserId?: number;
// }

// export interface AuthUserResponse {
//   user: {
//     username: string;
//     email: string;
//   };
//   userSub: string;
//   userDetails: User;
// }

// export interface UploadResponse {
//   message: string;
//   count: number;
// }

// export interface QcSummaryResult {
//   id: number;
//   description: string;
//   action: string;
//   status: string;
//   total_issues_flagged: number;
// }

// export interface QcRunResponse {
//   status: string;
//   message: string;
//   download_url: string;
//   summaries: QcSummaryResult[];
// }

// /* -------------------------------------------------------------------------- */
// /*                               API SETUP                                    */
// /* -------------------------------------------------------------------------- */

// export const api = createApi({
//   reducerPath: "api",

//   baseQuery: fetchBaseQuery({
//     baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,

//     prepareHeaders: async (headers) => {
//       const token = oktaAuth.getAccessToken();
//       if (token) {
//         headers.set("Authorization", `Bearer ${token}`);
//       }
//       return headers;
//     },
//   }),

//   tagTypes: [
//     "Projects",
//     "Tasks",
//     "Users",
//     "Teams",
//     "QcResults",
//   ],

//   endpoints: (build) => ({
//     /* --------------------------- AUTH USER -------------------------------- */

//     getAuthUser: build.query<AuthUserResponse, void>({
//       async queryFn(
//         _,
//         _api: BaseQueryApi,
//         _extraOptions,
//         fetchWithBQ,
//       ) {
//         try {
//           const claims = await oktaAuth.getUser();

//           if (!claims?.sub) {
//             return {
//               error: {
//                 status: 401,
//                 data: "User not authenticated",
//               } as FetchBaseQueryError,
//             };
//           }

//           const userSub = claims.sub;

//           const user = {
//             username:
//               claims.preferred_username ??
//               claims.email ??
//               "unknown",
//             email: claims.email ?? "",
//           };

//           const userDetailsResponse = await fetchWithBQ(
//             `/dashboard/users/${userSub}`,
//           );

//           if (userDetailsResponse.error) {
//             return {
//               error: {
//                 status: 500,
//                 data: "Failed to fetch user details",
//               } as FetchBaseQueryError,
//             };
//           }

//           return {
//             data: {
//               user,
//               userSub,
//               userDetails: userDetailsResponse.data as User,
//             },
//           };
//         } catch (err: any) {
//           return {
//             error: {
//               status: 500,
//               data: err?.message ?? "Authentication error",
//             } as FetchBaseQueryError,
//           };
//         }
//       },
//       providesTags: ["Users"],
//     }),

//     /* --------------------------- PROJECTS ---------------------------------- */

//     getProjects: build.query<Project[], void>({
//       query: () => "/dashboard/projects/",
//       providesTags: ["Projects"],
//     }),

//     createProject: build.mutation<Project, Partial<Project>>({
//       query: (project) => ({
//         url: "/dashboard/projects",
//         method: "POST",
//         body: project,
//       }),
//       invalidatesTags: ["Projects"],
//     }),

//     /* ---------------------------- TASKS ------------------------------------ */

//     getTasks: build.query<Task[], { projectId: number }>({
//       query: ({ projectId }) =>
//         `/dashboard/tasks?projectId=${projectId}`,
//       providesTags: ["Tasks"],
//     }),

//     getTasksByUser: build.query<Task[], number>({
//       query: (userId) => `/dashboard/tasks/user/${userId}`,
//       providesTags: ["Tasks"],
//     }),

//     createTask: build.mutation<Task, Partial<Task>>({
//       query: (task) => ({
//         url: "/dashboard/tasks",
//         method: "POST",
//         body: task,
//       }),
//       invalidatesTags: ["Tasks"],
//     }),

//     updateTaskStatus: build.mutation<
//       Task,
//       { taskId: number; status: string }
//     >({
//       query: ({ taskId, status }) => ({
//         url: `/dashboard/tasks/${taskId}/status`,
//         method: "PATCH",
//         body: { status },
//       }),
//       invalidatesTags: ["Tasks"],
//     }),

//     /* ----------------------------- USERS ----------------------------------- */

//     getUsers: build.query<User[], void>({
//       query: () => "/dashboard/users",
//       providesTags: ["Users"],
//     }),

//     getTeams: build.query<Team[], void>({
//       query: () => "/dashboard/teams",
//       providesTags: ["Teams"],
//     }),

//     search: build.query<SearchResults, string>({
//       query: (query) =>
//         `/dashboard/search?query=${query}`,
//     }),

//     /* --------------------------- QC PIPELINE ------------------------------- */

//     runQcChecks: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         url: "/qc/run_qc",
//         method: "POST",
//         body: formData,
//       }),
//       invalidatesTags: ["QcResults"],
//     }),

//     runMarketChecks: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         url: "/qc/market_check_and_process",
//         method: "POST",
//         body: formData,
//       }),
//       invalidatesTags: ["QcResults"],
//     }),

//     uploadFile: build.mutation<UploadResponse, FormData>({
//       query: (formData) => ({
//         url: "/upload/data",
//         method: "POST",
//         body: formData,
//       }),
//     }),
//   }),
// });

// /* -------------------------------------------------------------------------- */
// /*                               EXPORT HOOKS                                 */
// /* -------------------------------------------------------------------------- */

// export const {
//   useGetAuthUserQuery,
//   useGetProjectsQuery,
//   useCreateProjectMutation,
//   useGetTasksQuery,
//   useGetTasksByUserQuery,
//   useCreateTaskMutation,
//   useUpdateTaskStatusMutation,
//   useGetUsersQuery,
//   useGetTeamsQuery,
//   useSearchQuery,
//   useRunQcChecksMutation,
//   useRunMarketChecksMutation,
//   useUploadFileMutation,
// } = api;












































































// import {
//   createApi,
//   fetchBaseQuery,
//   FetchBaseQueryError,
// } from "@reduxjs/toolkit/query/react";
// import type { BaseQueryApi } from "@reduxjs/toolkit/query/react";

// /* -------------------------------------------------------------------------- */
// /*                               DUMMY AUTH                                    */
// /* -------------------------------------------------------------------------- */

// const fetchAuthSession = async () => ({
//   tokens: { accessToken: "DUMMY_ACCESS_TOKEN" },
//   userSub: "dummy-user-sub",
// });

// const getCurrentUser = async () => ({
//   username: "dummy_user",
//   email: "dummy_user@example.com",
//   userId: 1,
// });

// /* -------------------------------------------------------------------------- */
// /*                               INTERFACES                                   */
// /* -------------------------------------------------------------------------- */

// export interface Project {
//   id: number;
//   name: string;
//   description?: string;
//   startDate?: string;
//   endDate?: string;
// }

// export enum Priority {
//   Urgent = "Urgent",
//   High = "High",
//   Medium = "Medium",
//   Low = "Low",
//   Backlog = "Backlog",
// }

// export enum Status {
//   ToDo = "To Do",
//   WorkInProgress = "Work In Progress",
//   UnderReview = "Under Review",
//   Completed = "Completed",
// }

// export interface User {
//   userId?: number;
//   username: string;
//   email: string;
//   profilePictureUrl?: string;
//   teamId?: number;
// }

// export interface Attachment {
//   id: number;
//   fileURL: string;
//   fileName: string;
//   taskId: number;
//   uploadedById: number;
// }

// export interface Task {
//   id: number;
//   title: string;
//   description?: string;
//   status?: Status;
//   priority?: Priority;
//   tags?: string;
//   startDate?: string;
//   dueDate?: string;
//   points?: number;
//   projectId: number;
//   authorUserId?: number;
//   assignedUserId?: number;

//   author?: User;
//   assignee?: User;
//   comments?: any[];
//   attachments?: Attachment[];
// }

// export interface SearchResults {
//   tasks?: Task[];
//   projects?: Project[];
//   users?: User[];
// }

// export interface Team {
//   teamId: number;
//   teamName: string;
//   productOwnerUserId?: number;
//   projectManagerUserId?: number;
// }

// export interface AuthUserResponse {
//   user: {
//     username: string;
//     email: string;
//   };
//   userSub: string;
//   userDetails: User;
// }

// export interface UploadResponse {
//   message: string;
//   count: number;
// }

// export interface QcSummaryResult {
//   id: number;
//   description: string;
//   action: string;
//   status: string;
//   total_issues_flagged: number;
// }

// export interface QcRunResponse {
//   status: string;
//   message: string;
//   download_url: string;
//   summaries: QcSummaryResult[];
// }

// /* -------------------------------------------------------------------------- */
// /*                               API SETUP                                    */
// /* -------------------------------------------------------------------------- */

// export const api = createApi({
//   reducerPath: "api",
//   baseQuery: fetchBaseQuery({
//     baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
//     prepareHeaders: async (headers) => {
//       const session = await fetchAuthSession();
//       const token = session.tokens.accessToken;
//       if (token) {
//         headers.set("Authorization", `Bearer ${token}`);
//       }
//       return headers;
//     },
//   }),
//   tagTypes: ["Projects", "Tasks", "Users", "Teams", "QcResults"],
//   endpoints: (build) => ({
//     getAuthUser: build.query<AuthUserResponse, void>({
//       queryFn: async (_, _api: BaseQueryApi, _extra, fetchWithBQ) => {
//         try {
//           const user = await getCurrentUser();
//           const session = await fetchAuthSession();
//           const userSub = session.userSub;

//           const userDetailsResponse = await fetchWithBQ(
//             `/dashboard/users/${userSub}`
//           );

//           return {
//             data: {
//               user,
//               userSub,
//               userDetails: userDetailsResponse.data as User,
//             },
//           };
//         } catch (err: any) {
//           return {
//             error: {
//               status: 500,
//               data: err?.message ?? "Authentication error",
//             } as FetchBaseQueryError,
//           };
//         }
//       },
//       providesTags: ["Users"],
//     }),

//     getProjects: build.query<Project[], void>({
//       query: () => "/dashboard/projects/",
//       providesTags: ["Projects"],
//     }),

//     createProject: build.mutation<Project, Partial<Project>>({
//       query: (project) => ({
//         url: "/dashboard/projects",
//         method: "POST",
//         body: project,
//       }),
//       invalidatesTags: ["Projects"],
//     }),

//     getTasks: build.query<Task[], { projectId: number }>({
//       query: ({ projectId }) => `/dashboard/tasks?projectId=${projectId}`,
//       providesTags: ["Tasks"],
//     }),

//     getTasksByUser: build.query<Task[], number>({
//       query: (userId) => `/dashboard/tasks/user/${userId}`,
//       providesTags: ["Tasks"],
//     }),

//     createTask: build.mutation<Task, Partial<Task>>({
//       query: (task) => ({
//         url: "/dashboard/tasks",
//         method: "POST",
//         body: task,
//       }),
//       invalidatesTags: ["Tasks"],
//     }),

//     updateTaskStatus: build.mutation<Task, { taskId: number; status: string }>({
//       query: ({ taskId, status }) => ({
//         url: `/dashboard/tasks/${taskId}/status`,
//         method: "PATCH",
//         body: { status },
//       }),
//       invalidatesTags: ["Tasks"],
//     }),

//     getUsers: build.query<User[], void>({
//       query: () => "/dashboard/users",
//       providesTags: ["Users"],
//     }),

//     getTeams: build.query<Team[], void>({
//       query: () => "/dashboard/teams",
//       providesTags: ["Teams"],
//     }),

//     search: build.query<SearchResults, string>({
//       query: (query) => `/dashboard/search?query=${query}`,
//     }),

//     runQcChecks: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         url: "/qc/run_qc",
//         method: "POST",
//         body: formData,
//       }),
//       invalidatesTags: ["QcResults"],
//     }),

//     runMarketChecks: build.mutation<QcRunResponse, FormData>({
//       query: (formData) => ({
//         url: "/qc/market_check_and_process",
//         method: "POST",
//         body: formData,
//       }),
//       invalidatesTags: ["QcResults"],
//     }),

//     uploadFile: build.mutation<UploadResponse, FormData>({
//       query: (formData) => ({
//         url: "/upload/data",
//         method: "POST",
//         body: formData,
//       }),
//     }),
//   }),
// });

// /* -------------------------------------------------------------------------- */
// /*                               EXPORT HOOKS                                 */
// /* -------------------------------------------------------------------------- */

// export const {
//   useGetAuthUserQuery,
//   useGetProjectsQuery,
//   useCreateProjectMutation,
//   useGetTasksQuery,
//   useGetTasksByUserQuery,
//   useCreateTaskMutation,
//   useUpdateTaskStatusMutation,
//   useGetUsersQuery,
//   useGetTeamsQuery,
//   useSearchQuery,
//   useRunQcChecksMutation,
//   useRunMarketChecksMutation,
//   useUploadFileMutation,
// } = api;
