const express = require('express');
const router = express.Router();
const { pool } = require('../config/db');
const { logger } = require('../config/logger');

router.post('/single', async (req, res) => {
  const { page, timestamp } = req.body;

  // Validate required fields
  if (!page || !timestamp) {
    logger.warn('Missing required fields in /single request', { page, timestamp });
    return res.status(400).json({
      error: 'Missing required fields',
      required: ['page', 'timestamp']
    });
  }
  try {
    // Parse timestamp in format YYYY-MM-DD_HH:mm
    const [datePart, timePart] = timestamp.split('_');
    const [hour] = timePart.split(':');

    const result = await pool.query(
      `INSERT INTO page_views (page, hour, page_view) 
       VALUES ($1, $2, 1) 
       ON CONFLICT (page, hour) 
       DO UPDATE SET page_view = page_views.page_view + 1 
       RETURNING id, page_views.page_view`,
      [page, hour]
    );

    const response = {
      success: true,
      id: result.rows[0].id,
      page_view: result.rows[0].page_view
    };
    logger.info('Successfully recorded single page view', { page, hour: hour, views: result.rows[0].page_view });
    res.status(201).json(response);
  } catch (error) {
    logger.error('Failed to record single page view', { error: error.message, page, timestamp });
    res.status(500).json({ error: 'Failed to record page view' });
  }
});

router.post('/multi', async (req, res) => {
  try {
    if (!req.body || typeof req.body !== 'object') {
      logger.warn('Invalid request body format in /multi request', { body: req.body });
      return res.status(400).json({
        error: 'Invalid request body format',
        expected: '{ "page.html": { "YYYY-MM-DD_HH:mm": count, ... }, ... }'
      });
    }

    const insertPromises = [];

    // Process each page
    for (const [page, timestamps] of Object.entries(req.body)) {
      if (typeof timestamps !== 'object') {
        return res.status(400).json({
          error: `Invalid timestamp data for page: ${page}`,
          expected: '{ "YYYY-MM-DD_HH:mm": count, ... }'
        });
      }

      // Process each timestamp for the page
      for (const [timestamp, count] of Object.entries(timestamps)) {
        if (typeof count !== 'number' || count <= 0) {
          return res.status(400).json({
            error: `Invalid count for page ${page} at timestamp ${timestamp}`,
            expected: 'Positive number'
          });
        }

        // Extract hour from timestamp
        const [datePart, timePart] = timestamp.split('_');
        const [hour] = timePart.split(':');

        // Add upsert query for this page and hour
        const query = {
          text: `INSERT INTO page_views (page, hour, page_view) 
                VALUES ($1, $2, $3) 
                ON CONFLICT (page, hour) 
                DO UPDATE SET page_view = page_views.page_view + $3 
                RETURNING id, page_views.page_view`,
          values: [page, hour, count]
        };

        insertPromises.push(pool.query(query));
      }
    }

    // Execute all upsert queries
    const results = await Promise.all(insertPromises);

    const response = {
      success: true,
      updates: results.map(result => ({
        id: result.rows[0].id,
        page_view: result.rows[0].page_view
      }))
    };
    logger.info('Successfully recorded multiple page views', { 
      pageCount: Object.keys(req.body).length,
      totalUpdates: results.length
    });
    res.status(201).json(response);
  } catch (error) {
    logger.error('Failed to record multiple page views', { error: error.message });
    res.status(500).json({ error: 'Failed to record page views' });
  }
});

module.exports = router;
