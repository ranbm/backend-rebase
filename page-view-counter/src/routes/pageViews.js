import express from 'express';
const router = express.Router();
import { pool } from '../config/db.js';
import { logger } from '../config/logger.js';

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
    // Create a proper timestamp for hour_start
    const hourStart = `${datePart} ${hour}:00:00`;

    const result = await pool.query(
      `INSERT INTO page_hourly_views (page_id, hour_start, view_count) 
       VALUES ($1, $2, 1) 
       ON CONFLICT (page_id, hour_start) 
       DO UPDATE SET view_count = page_hourly_views.view_count + 1 
       RETURNING page_id, hour_start, view_count`,
      [page, hourStart]
    );

    const response = {
      success: true,
      page_id: result.rows[0].page_id,
      hour_start: result.rows[0].hour_start,
      view_count: result.rows[0].view_count
    };
    logger.info('Successfully recorded single page view', { page, hour: hour, views: result.rows[0].view_count });
    res.status(201).json(response);
  } catch (error) {
    logger.error('Failed to record single page view', { error: error.message, page, timestamp });
    res.status(500).json({ error: 'Failed to record page view', error });
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
        // Create a proper timestamp for hour_start
        const hourStart = `${datePart} ${hour}:00:00`;

        // Add upsert query for this page and hour
        const query = {
          text: `INSERT INTO page_hourly_views (page_id, hour_start, view_count) 
                VALUES ($1, $2, $3) 
                ON CONFLICT (page_id, hour_start) 
                DO UPDATE SET view_count = page_hourly_views.view_count + $3 
                RETURNING page_id, hour_start, view_count`,
          values: [page, hourStart, count]
        };

        insertPromises.push(pool.query(query));
      }
    }

    // Execute all upsert queries
    const results = await Promise.all(insertPromises);

    const response = {
      success: true,
      updates: results.map(result => ({
        page_id: result.rows[0].page_id,
        hour_start: result.rows[0].hour_start,
        view_count: result.rows[0].view_count
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

export default router;
