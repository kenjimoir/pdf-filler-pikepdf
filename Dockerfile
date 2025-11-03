FROM node:18

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port (Render.com uses 10000, Railway uses dynamic port)
# Use environment variable PORT or default to 8080
EXPOSE 8080

# Start the application
CMD ["node", "index.js"]

