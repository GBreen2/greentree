FROM php:8.0-cli

# Set working directory
WORKDIR /usr/src/app

# Copy the PHP code to container
COPY . .

# Set the command to run the PHP server
CMD ["php", "-S", "0.0.0.0:3000", "-t", "."]
