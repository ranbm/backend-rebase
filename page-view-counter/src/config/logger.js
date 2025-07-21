import express from 'express'
import getmac from 'getmac';
import { createLogger } from "logzio-nodejs";
import winston from 'winston';

const weAreInProduction = (process.env.NODE_ENV || '').toLowerCase().startsWith('prod');

const { combine, timestamp, colorize, printf } = winston.format;

const myFormat = printf(({ level, message, timestamp }) => {
    return `${(timestamp).toString().replace("T", " ").replace("Z", "")} ${level}: ${message}`;
});

class MyLogger {

    winstonLogger;
    logzioLogger;

    constructor(logzioLogger) {
        this.logzioLogger = logzioLogger;
        this.logzioLogger.extraFields = { ...(this.logzioLogger.extraFields || {}), mymac: getmac(), pid: process.pid };
        this.winstonLogger = winston.createLogger({
            level: weAreInProduction ? 'info' : 'debug',
            format: combine(
                colorize(),
                timestamp(),
                myFormat,
            ),
            transports: [new winston.transports.Console()]
        });
    }

    debug(message, obj) {
        this.logzioLogger.log({ ...(obj || {}), message, level: 'debug' });
        this.winstonLogger.debug({ ...(obj || {}), message })
    }

    info(message, obj) {
        this.logzioLogger.log({ ...(obj || {}), message, level: 'info' });
        this.winstonLogger.info({ ...(obj || {}), message })
    }

    warn(message, obj) {
        this.logzioLogger.log({ ...(obj || {}), message, level: 'warn' });
        this.winstonLogger.warn({ ...(obj || {}), message })
    }

    error(message, obj) {
        this.logzioLogger.log({ ...(obj || {}), message, level: 'error' });
        this.winstonLogger.error({ ...(obj || {}), message })
    }
}

// Replace these parameters with your configuration
const lgzio = createLogger({
    token: 'mFJpupXOLGfnACdjyGZlomwDdpxVfUFI',
    protocol: 'https',
    host: 'listener-eu.logz.io',
    port: '8071',
    type: 'moshe-diamond-logs',
    debug: !weAreInProduction,
});

// Create and export the logger instance
const logger = new MyLogger(lgzio);
export { logger };
