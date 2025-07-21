import express from 'express';
import { pool, testConnection } from './config/db.js';
import { logger } from './config/logger.js';
const app = express();

// Middleware for parsing JSON bodies
app.use(express.json());

// Import routes
import pageViewsRouter from './routes/pageViews.js';

// Use routes
app.use('/page-views', pageViewsRouter);

// Health check endpoint
app.get('/health', async (req, res) => {
    try {
        const dbConnected = await testConnection();
        const status = {
            status: 'ok',
            database: dbConnected ? 'connected' : 'disconnected'
        };
        logger.info('Health check successful', status);
        res.json(status);
    } catch (err) {
        const errorStatus = {
            status: 'error',
            database: 'error',
            message: err.message
        };
        logger.error('Health check failed', { error: err.message });
        res.status(500).json(errorStatus);
    }
});

// Start server after testing database connection
const startServer = async () => {
    try {
        // Test database connection first
        const dbConnected = await testConnection();
        if (!dbConnected) {
            logger.error('Failed to connect to database. Retrying in 5 seconds...');
            setTimeout(startServer, 5000);
            return;
        }

        const PORT = process.env.PORT || 3000;
        app.listen(PORT, () => {
            logger.info(`Server started successfully`, { port: PORT });
        });
    } catch (err) {
        logger.error('Failed to start server', { error: err.message });
        process.exit(1);
    }
};

startServer();
