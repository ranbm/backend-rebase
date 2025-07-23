const express = require('express');
const router = express.Router();
const queueService = require('../services/queueService');

// Helper function to format data
const formatPageView = (page, timestamp, views) => ({
    [page]: {
        [timestamp]: views
    }
});

// POST /single - Handle single page view
router.post('/single', async (req, res) => {
    try {
        const { page, timestamp } = req.body;
        
        if (!page || !timestamp) {
            return res.status(400).json({ error: 'Page and timestamp are required' });
        }

        const formattedData = formatPageView(page, timestamp, 1);
        const queueName = await queueService.publishToRandomQueue(formattedData);

        res.status(201).json({
            message: 'Page view data published successfully',
            queue: queueName,
            data: formattedData
        });
    } catch (error) {
        console.error('Error publishing page view:', error);
        res.status(500).json({ error: 'Failed to publish page view data' });
    }
});

// POST /multi - Handle multiple page views
router.post('/multi', async (req, res) => {
    try {
        // Validate input format
        if (!req.body || typeof req.body !== 'object') {
            return res.status(400).json({ error: 'Invalid data format' });
        }

        // The data is already in the correct format
        const queueName = await queueService.publishToRandomQueue(req.body);

        res.status(201).json({
            message: 'Multiple page views data published successfully',
            queue: queueName,
            data: req.body
        });
    } catch (error) {
        console.error('Error publishing multiple page views:', error);
        res.status(500).json({ error: 'Failed to publish page views data' });
    }
});

module.exports = router;
