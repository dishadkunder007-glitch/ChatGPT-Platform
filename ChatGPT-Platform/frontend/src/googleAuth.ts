const GOOGLE_CLIENT_ID =
  (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
  '234064504966-mp94u70iusepkhkfnb9g4tipk6pbkm97.apps.googleusercontent.com';

export interface GoogleProfileResult {
  credential: string;
  email: string;
  name: string;
  avatar_url: string;
  sub: string;
}

/**
 * Triggers Google's official Account Chooser popup modal using Google Identity Services (GSI).
 * Displays all logged-in Google accounts on the browser and lets the user pick one.
 */
export function triggerGoogleAccountChooser(): Promise<GoogleProfileResult> {
  return new Promise((resolve, reject) => {
    // Check if Google GSI SDK is loaded on window
    const gWindow = window as any;
    if (gWindow.google && gWindow.google.accounts && gWindow.google.accounts.oauth2) {
      try {
        const client = gWindow.google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: 'email profile openid',
          prompt: 'select_account',
          callback: async (tokenResponse: any) => {
            if (tokenResponse.error) {
              if (tokenResponse.error === 'popup_closed_by_user') {
                return reject(new Error('Google sign-in popup was closed.'));
              }
              return reject(new Error(`Google sign-in error: ${tokenResponse.error}`));
            }

            if (!tokenResponse.access_token) {
              return reject(new Error('No access token received from Google.'));
            }

            try {
              // Fetch user profile directly from Google userinfo API
              const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                headers: {
                  Authorization: `Bearer ${tokenResponse.access_token}`,
                },
              });

              if (!res.ok) {
                throw new Error('Failed to fetch Google profile information.');
              }

              const profile = await res.json();
              resolve({
                credential: tokenResponse.access_token,
                email: profile.email || '',
                name: profile.name || profile.given_name || profile.email?.split('@')[0] || 'Google User',
                avatar_url: profile.picture || '',
                sub: profile.sub || '',
              });
            } catch (fetchErr: any) {
              reject(fetchErr);
            }
          },
        });

        client.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (initErr: any) {
        console.warn('Google GSI init failed, falling back to popup flow:', initErr);
      }
    }

    // Fallback: Open standard Google OAuth2 account selector window if GSI not ready
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(
      GOOGLE_CLIENT_ID
    )}&redirect_uri=${encodeURIComponent(
      window.location.origin
    )}&response_type=token&scope=email%20profile%20openid&prompt=select_account`;

    const popup = window.open(authUrl, 'GoogleSignIn', 'width=500,height=600,menubar=no,toolbar=no');
    if (!popup) {
      return reject(new Error('Popup blocked by browser. Please allow popups for this site.'));
    }

    reject(new Error('google_gsi_fallback'));
  });
}
