import pygame
import time
import math
from utils import scale_image, blit_rotate_center
import neat
pygame.font.init()


# Load configuration file
config_path = "./neat-config.txt"
config = neat.config.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    config_path
)


scaling_factor = 1

GRASS = scale_image(pygame.image.load("imgs/grass.jpg"), 2.5 * scaling_factor)
TRACK = scale_image(pygame.image.load("imgs/track.png"), 0.9 * scaling_factor)

TRACK_BORDER = scale_image(pygame.image.load("imgs/track-border.png"), 0.9 * scaling_factor)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

FINISH = scale_image(pygame.image.load("imgs/finish.png"), scaling_factor)
FINISH_MASK = pygame.mask.from_surface(FINISH)

START_POSITION = (180 * scaling_factor, 200 * scaling_factor)
FINISH_POSITION = (130 * scaling_factor, 250 * scaling_factor)

RED_CAR = scale_image(pygame.image.load("imgs/red-car.png"), 0.55 * scaling_factor)

WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Racing Game!")

MAIN_FONT = pygame.font.SysFont("comicsans", 44)

FPS = 60

PATH = [(175, 119), (110, 70), (56, 133), (70, 481), (318, 731), (404, 680), (418, 521), (507, 475), (600, 551), (613, 715), (736, 713),
        (734, 399), (611, 357), (409, 343), (433, 257), (697, 258), (738, 123), (581, 71), (303, 78), (275, 377), (176, 388), (178, 260)]

class AbstractCar:
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.8

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()

    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()

    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel

        self.y -= vertical
        self.x -= horizontal

    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = mask.overlap(car_mask, offset)
        return poi

    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0


class PlayerCar(AbstractCar):
    IMG = RED_CAR
    START_POS = START_POSITION

    def __init__(self, max_vel, rotation_vel):
        super().__init__(max_vel, rotation_vel)
        self.sensor_length = 150  # Length of the sensor rays
        self.num_sensors = 5  # Number of sensors (rays)
        self.sensors = []
        self.sensor_data = []
        self.height = self.img.get_height()
        self.width = self.img.get_width()

    def update_sensors(self, obstacles):
        self.sensors.clear()
        self.sensor_data.clear()

        # Calculate the center of the car
        car_center_x = self.x + self.width / 2
        car_center_y = self.y + self.height / 2

        # Calculate the front of the car
        front_x = car_center_x + (self.height / 2) * math.cos(math.radians(self.angle+90))
        front_y = car_center_y - (self.height / 2) * math.sin(math.radians(self.angle+90))

        # Define sensor angles relative to the car's angle
        angles = [-45, -22.5, 0, 22.5, 45]  # Angles for the sensors in degrees

        for angle_offset in angles:
            # Calculate the sensor angle
            sensor_angle = self.angle + angle_offset + 90
            sensor_angle_rad = math.radians(sensor_angle)

            # Calculate the end point of the sensor ray starting from the front of the car
            end_x = front_x + self.sensor_length * math.cos(sensor_angle_rad)
            end_y = front_y - self.sensor_length * math.sin(sensor_angle_rad)  # Note the negative sign for y

            closest_distance = self.sensor_length
            closest_point = (end_x, end_y)

            # Check for collision with each obstacle
            for obstacle in obstacles:
                intersect_point, distance = self.ray_intersect((front_x, front_y), (end_x, end_y), obstacle)
                if intersect_point and distance < closest_distance:
                    closest_distance = distance
                    closest_point = intersect_point

            self.sensors.append((front_x, front_y, closest_point[0], closest_point[1]))
            self.sensor_data.append(closest_distance / self.sensor_length)  # Normalize distance

    def ray_intersect(self, start, end, obstacle_mask):
        x1, y1 = start
        x2, y2 = end

        for i in range(self.sensor_length):
            u = i / self.sensor_length
            x = int(x1 + u * (x2 - x1))
            y = int(y1 + u * (y2 - y1))

            if obstacle_mask.get_at((x, y)):
                return (x, y), math.sqrt((x - x1) ** 2 + (y - y1) ** 2)

        return None, self.sensor_length

    def draw_sensors(self, win):
        # Draw the sensors for visualization
        for sensor in self.sensors:
            pygame.draw.line(win, (255, 0, 0), (sensor[0], sensor[1]), (sensor[2], sensor[3]), 3)

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        self.vel = -self.vel
        self.move()


def draw(win, images, player_car: PlayerCar):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)

    # for point in PATH:
    #     pygame.draw.circle(win, (255, 0, 0), point, 5)

    # Update and draw sensors
    player_car.update_sensors([TRACK_BORDER_MASK])
    player_car.draw_sensors(WIN)

    pygame.display.update()


def move_player(player_car):
    keys = pygame.key.get_pressed()
    moved = False

    if keys[pygame.K_a]:
        player_car.rotate(left=True)
    if keys[pygame.K_d]:
        player_car.rotate(right=True)
    if keys[pygame.K_w]:
        moved = True
        player_car.move_forward()
    if keys[pygame.K_s]:
        moved = True
        player_car.move_backward()

    if not moved:
        player_car.reduce_speed()


def handle_collision(player_car: PlayerCar):
    # Check if player hitts the border
    if player_car.collide(TRACK_BORDER_MASK) != None:
        player_car.reset()

	# Check if the player has finished
    player_finish_poi_collide = player_car.collide(
        FINISH_MASK, *FINISH_POSITION)
    if player_finish_poi_collide != None:
        if player_finish_poi_collide[1] == 0:
            player_car.reset()
        else:
            player_car.reset()


def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        player_car = PlayerCar(8, 4)
        fitness = run_simulation(player_car, net)
        genome.fitness = fitness


images = [(GRASS, (0, 0)), (TRACK, (0, 0)),
          (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]

def run_simulation(player_car: PlayerCar, net):
    clock = pygame.time.Clock()
    run = True
    fitness = 0

    while run:
        clock.tick(FPS)

        # Get sensor data and feed it to the neural network
        player_car.update_sensors([TRACK_BORDER_MASK])
        output = net.activate(player_car.sensor_data)

        # Use the network output to control the car
        steer = output[0]

        if steer > 0.5:
            player_car.rotate(right=True)
        elif steer < -0.5:
            player_car.rotate(left=True)

        player_car.move_forward()

        draw(WIN, images, player_car)

        # Check for collision or finish line
        if player_car.collide(TRACK_BORDER_MASK) is not None:
            fitness -= 1
            run = False
        else:
            fitness += 1  # Increase fitness for surviving longer

        # Add any other conditions to end the simulation
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

    return fitness

p = neat.Population(config)

p.add_reporter(neat.StdOutReporter(True))
stats = neat.StatisticsReporter()
p.add_reporter(stats)

winner = p.run(eval_genomes, n=50)  # Run for 50 generations or until a solution is found

print(f'Best genome:\n{winner}')

