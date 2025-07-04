import { useState } from 'react';
import {
    Box,
    TextField,
    Button,
} from '@mui/material';
import axios from 'axios';


const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'HubSpot': 'hubspot'
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);

    const handleLoad = async () => {
        try {
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(
                `http://localhost:8000/integrations/${endpointMapping[integrationType]}/load`, 
                formData
            );
            setLoadedData(response.data);
        } catch (e) {
            alert(e?.response?.data?.detail || 'Failed to load data');
        }
    };

    
    const displayData = loadedData 
        ? JSON.stringify(loadedData, null, 2)  
        : '';

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                <TextField
                    label="Loaded Data"
                    value={displayData}
                    sx={{ mt: 2 }}
                    InputLabelProps={{ shrink: true }}
                    disabled
                    multiline
                    minRows={10}
                    maxRows={20}
                    fullWidth
                />
                <Button
                    onClick={handleLoad}
                    sx={{ mt: 2 }}
                    variant='contained'
                >
                    Load Data
                </Button>
                <Button
                    onClick={() => setLoadedData(null)}
                    sx={{ mt: 1 }}
                    variant='contained'
                    color="secondary"
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
};