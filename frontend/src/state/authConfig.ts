// import { OktaAuth } from '@okta/okta-auth-js';

// // 1. Safe check for window/browser environment
// const isBrowser = typeof window !== 'undefined';

// const isDevelopment = isBrowser && window.location.hostname === 'localhost';

// // 2. Export a config object instead of the live instance directly to be safe, 
// // OR initialize it only if in browser.
// export const oktaAuth = isBrowser 
//   ? new OktaAuth({
//       issuer: 'https://nielsen.okta.com/oauth2/default',
//       clientId: '0oa25qglsixBrnZNV0h8',
      
//       redirectUri: isDevelopment 
//         ? 'http://localhost:3000/login/callback' 
//         : 'http://automationportal-app-np-1996887397.ap-south-1.elb.amazonaws.com/login/callback',
      
//       postLogoutRedirectUri: isDevelopment
//         ? 'http://localhost:3000'
//         : 'http://automationportal-app-np-1996887397.ap-south-1.elb.amazonaws.com',

//       scopes: ['openid', 'profile', 'email'],
//       pkce: true,
//     })
//   : null; // Return null on server side


import { OktaAuth } from '@okta/okta-auth-js';

const isBrowser = typeof window !== 'undefined';

// ⚠️ IMPORTANT: We are forcing the AWS URL even for development
// because that is likely the ONLY URL your Admin allowed.
const IDP_URL = 'https://sportsautomation.nlsn.media';

export const oktaAuth = isBrowser 
  ? new OktaAuth({
      issuer: 'https://nielsen.okta.com/oauth2/default',
      clientId: '0oa26k5oa7keTeGqs0h8',
      
      // Force the production URL to satisfy the Okta Admin settings
      redirectUri: `${IDP_URL}/`,
      postLogoutRedirectUri: IDP_URL,

      scopes: ['openid', 'profile', 'email'],
      pkce: true,
    })
  : null;