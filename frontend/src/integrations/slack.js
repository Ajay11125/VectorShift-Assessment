import { useState, useEffect } from 'react';
import {
    Box,
    Button,
    CircularProgress
} from '@mui/material';
import axios from 'axios'; 

export const HubSpotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(
                'http://localhost:8000/integrations/hubspot/authorize', 
                formData
            );
            
            const authURL = response?.data;
            const newWindow = window.open(
                authURL, 
                'HubSpot Authorization', 
                'width=600,height=600'
            );

            const pollTimer = setInterval(() => {
                if (newWindow?.closed) {
                    clearInterval(pollTimer);
                    handleWindowClosed();
                }
            }, 200);
        } catch (error) {
            setIsConnecting(false);
            alert(error?.response?.data?.detail || 'Failed to connect to HubSpot');
        }
    };

    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(
                'http://localhost:8000/integrations/hubspot/credentials', 
                formData
            );
            
            const credentials = response.data;
            if (credentials) {
                setIsConnected(true);
                setIntegrationParams(prev => ({
                    ...prev,
                    credentials: credentials,
                    type: 'HubSpot'
                }));
            }
        } catch (error) {
            alert(error?.response?.data?.detail || 'Failed to get HubSpot credentials');
        } finally {
            setIsConnecting(false);
        }
    };

    useEffect(() => {
        setIsConnected(!!integrationParams?.credentials);
    }, [integrationParams]);

    return (
        <Box sx={{ mt: 2 }}>
            <Box display='flex' alignItems='center' justifyContent='center' sx={{ mt: 2 }}>
                <Button 
                    variant='contained' 
                    onClick={isConnected ? null : handleConnectClick}
                    color={isConnected ? 'success' : 'primary'}
                    disabled={isConnecting}
                    sx={{
                        pointerEvents: isConnected ? 'none' : 'auto',
                        cursor: isConnected ? 'default' : 'pointer'
                    }}
                >
                    {isConnected ? 'HubSpot Connected' : 
                     isConnecting ? <CircularProgress size={20} /> : 'Connect to HubSpot'}
                </Button>
            </Box>
        </Box>
    );
};