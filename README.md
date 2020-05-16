# Rideshare

This repository reflects the 4 stage process we followed for creating the backend of Rideshare.

Stage 1: Build APIs

Stage 2: Dockerised APIs into 1 docker container 

Stage 3: Seperated Rides and Users database, APIs as seperate containers running on seperate Amazon EC2 instances connected via load balancer

Stage 4: Built a fault tolerant, highly available database as a service for the RideShare application. Our DBaaS has High Availability and Scalability implemented with Zookeeper and RabbitMQ.

SSH into the following instances and clone this repository:
User instance IP: 54.82.244.44
Rides instance IP: 52.2.156.61
DBaaS instance IP: 52.203.199.62

To run the code after cloning:

1. Setup user service:
$cd cloud/stage4/assignment3/users
$docker-compose up --build

2. Setup user service:
$cd cloud/stage4/assignment3/rides
$docker-compose up --build

3. Set up DBaaS:
$cd cloud/stage4/zook
$docker-compose up --build --scale worker=3

Then send requests to the instances.
DONE!


