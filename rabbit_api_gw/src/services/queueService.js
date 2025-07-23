const amqp = require('amqplib');

class QueueService {
    constructor() {
        this.channel = null;
        this.queueNames = ['page_views1', 'page_views2', 'page_views3', 'page_views4'];
    }

    async connect(url) {
        try {
            const connection = await amqp.connect(url);
            this.channel = await connection.createChannel();
            await this.initializeQueues();
            console.log('Connected to RabbitMQ and initialized queues');
        } catch (error) {
            console.error('Error connecting to RabbitMQ:', error);
            throw error;
        }
    }

    async initializeQueues() {
        for (const queueName of this.queueNames) {
            await this.channel.assertQueue(queueName, { durable: true });
        }
    }

    getRandomQueue() {
        const randomIndex = Math.floor(Math.random() * this.queueNames.length);
        return this.queueNames[randomIndex];
    }

    async publishToRandomQueue(data) {
        const queueName = this.getRandomQueue();
        await this.channel.sendToQueue(
            queueName,
            Buffer.from(JSON.stringify(data)),
            { persistent: true }
        );
        return queueName;
    }
}

module.exports = new QueueService();
