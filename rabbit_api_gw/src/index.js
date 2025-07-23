const express = require('express');
require('dotenv').config();

const queueService = require('./services/queueService');
const pageViewRoutes = require('./routes/pageViewRoutes');

const app = express();
app.use(express.json());

// Use routes
app.use('/page-views', pageViewRoutes);

// Start server
const AMQP_URL = process.env.AMQP_URL || 'amqp://localhost:5672';
const PORT = process.env.PORT || 3000;

async function startServer() {
    try {
        await queueService.connect(AMQP_URL);
        app.listen(PORT, () => {
            console.log(`Server running on port ${PORT}`);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();
