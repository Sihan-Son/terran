import pygame
import random
import sys
import math
import os
from datetime import datetime
from collections import deque

# --- 게임 설정 (v10) ---
GRID_SIZE = 50
CELL_SIZE = 15
INFO_PANEL_WIDTH = 250
SCREEN_WIDTH = GRID_SIZE * CELL_SIZE + INFO_PANEL_WIDTH
SCREEN_HEIGHT = GRID_SIZE * CELL_SIZE
FPS = 15
NUM_FACTIONS = 5
MAX_TURNS = 2500 # 턴 증가

# --- 게임 규칙 상수 ---
SOLDIER_COST = 200
INITIAL_CAPTURE_COST = 50
MAX_SOLDIERS_PER_CELL = 150
MAX_SOLDIERS_PER_FACTION = 1000
MIN_SOLDIERS_TO_ATTACK = 10
MIN_SOLDIERS_TO_CAPTURE_EMPTY = 3
CAPITAL_DEFENSE_RATIO = 0.25
EARLY_GAME_TURNS = 300
EXPANSION_PRIORITY_TURNS = 500
ATTACK_SURVIVOR_RATIO = 0.3
MOUNTAIN_DEFENSE_BONUS = 1.15
CAPITAL_SAFETY_DISTANCE = 5
HOSTILITY_BONUS = 1.2

AI_TRAITS = ['expansionist', 'conqueror', 'defender']

# --- 지형 상수 ---
TERRAIN_TYPES = {
    'plains': {'color': (220, 220, 220), 'pop_modifier': 1.0, 'capture_time': 1, 'name': 'Plains'},
    'farmland': {'color': (245, 222, 179), 'pop_modifier': 2.0, 'capture_time': 2, 'name': 'Farmland'},
    'mountain': {'color': (139, 139, 139), 'pop_modifier': 0.5, 'capture_time': 1, 'name': 'Mountain'},
    'lake': {'color': (100, 149, 237), 'pop_modifier': 0, 'capture_time': -1, 'name': 'Lake'}
}

# --- 색상 정의 ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PANEL_BG = (30, 30, 40)
FACTION_COLORS = [
    (255, 50, 50), (50, 255, 50), (50, 50, 255),
    (255, 255, 50), (255, 50, 255)
]

# --- 데이터 클래스 ---
class Cell:
    def __init__(self, terrain_type):
        self.owner = None
        self.soldiers = 0
        self.terrain = terrain_type
        self.capturing_faction = None
        self.capture_timer = 0

# --- 메인 게임 클래스 ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Terran: Territory Conquest v10")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("sans", 18)
        self.small_font = pygame.font.SysFont("sans", 16)
        self.grid, self.lake_tiles, self.lake_perimeter = self._generate_map()
        self.factions = []
        self.turn = 0
        self.game_over = False
        self.winner = None
        self.log_file = None
        self.current_capture_cost = INITIAL_CAPTURE_COST
        self._setup_logging()
        self._setup_initial_state()

    def _generate_map(self):
        grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        lake_tiles = set()
        lx, ly = random.randint(10, GRID_SIZE-10), random.randint(10, GRID_SIZE-10)
        for _ in range(random.randint(5,9)):
            lake_tiles.add((lx, ly))
            lx += random.choice([-1,0,1]); ly += random.choice([-1,0,1])
            lx = max(0, min(GRID_SIZE-1, lx)); ly = max(0, min(GRID_SIZE-1, ly))
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if (x,y) in lake_tiles: grid[y][x] = Cell('lake')
                else:
                    rand_val = random.random()
                    if rand_val < 0.15: terrain_type = 'mountain'
                    elif rand_val < 0.40: terrain_type = 'farmland'
                    else: terrain_type = 'plains'
                    grid[y][x] = Cell(terrain_type)
        perimeter = set()
        for x,y in lake_tiles:
            for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx,ny=x+dx,y+dy
                if 0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE and (nx,ny) not in lake_tiles:
                    perimeter.add((nx,ny))
        return grid, lake_tiles, perimeter

    def _setup_logging(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"logs/game_log_{timestamp}.txt"
        self.log_file = open(log_filename, "w")
        self.log_file.write(f"Game Started: {timestamp}\n")
        self.log_file.write("Turn,FactionID,Population,Soldiers,Territory\n")

    def _write_log(self):
        if self.turn % 10 != 0: return
        for faction in self.factions:
            if faction['is_alive']:
                log_line = f"{self.turn},{faction['id'] + 1},{faction['total_population']},{faction['total_soldiers']},{faction['territory_count']}\n"
                self.log_file.write(log_line)

    def _setup_initial_state(self):
        faction_start_positions = []
        assigned_traits_count = {'defender': 0}
        
        for i in range(NUM_FACTIONS):
            while True:
                x = random.randint(1, GRID_SIZE - 2)
                y = random.randint(1, GRID_SIZE - 2)
                
                # Check if 3x3 capital zone is valid (within bounds and no lakes)
                is_valid_capital_zone = True
                temp_capital_zone = set()
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        cx, cy = x + dx, y + dy
                        if not (0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE) or self.grid[cy][cx].terrain == 'lake':
                            is_valid_capital_zone = False
                            break
                        temp_capital_zone.add((cx, cy))
                    if not is_valid_capital_zone:
                        break
                
                # Check if this capital zone overlaps with existing ones
                for existing_faction in self.factions:
                    if not temp_capital_zone.isdisjoint(existing_faction['capital_zone']):
                        is_valid_capital_zone = False
                        break

                if is_valid_capital_zone:
                    faction_start_positions.append((x, y, temp_capital_zone))
                    break

        for i, (x, y, capital_zone) in enumerate(faction_start_positions):
            # Assign AI trait, ensuring only one 'defender' if possible
            available_traits = [t for t in AI_TRAITS]
            if assigned_traits_count['defender'] >= 1:
                available_traits.remove('defender')
            
            assigned_trait = random.choice(available_traits)
            if assigned_trait == 'defender':
                assigned_traits_count['defender'] += 1

            self.factions.append({
                'id': i, 'color': FACTION_COLORS[i], 'is_alive': True,
                'total_population': 500, 'total_soldiers': 0, 'territory_count': 0,
                'hostility': random.uniform(0.4, 1.0),
                'capital_zone': capital_zone,
                'capital_core': (x, y),
                'vendetta_target': None,
                'ai_trait': assigned_trait
            })
            for cx, cy in capital_zone:
                self.grid[cy][cx].owner = i
            self.grid[y][x].soldiers = 10

    def _handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.log_file.close()
                pygame.quit()
                sys.exit()

    def _update_game_state(self):
        if self.game_over: return
        self.turn += 1

        if self.turn % 300 == 0 and self.turn > 0:
            self._reassign_ai_traits()

        # 점령 비용 증가
        

        

        self._process_captures()

        for faction in self.factions:
            if not faction['is_alive']: continue
            faction['territory_count'] = 0
            faction['total_soldiers'] = 0
            all_cells = {(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if self.grid[y][x].owner == faction['id']}
            faction['main_territory'] = max(self._find_territory_groups(all_cells), key=len) if all_cells else set()

            # 수도 안전 여부 확인 및 호전성 증가
            is_capital_safe = True
            capital_core_x, capital_core_y = faction['capital_core']
            for y_offset in range(-CAPITAL_SAFETY_DISTANCE, CAPITAL_SAFETY_DISTANCE + 1):
                for x_offset in range(-CAPITAL_SAFETY_DISTANCE, CAPITAL_SAFETY_DISTANCE + 1):
                    nx, ny = capital_core_x + x_offset, capital_core_y + y_offset
                    if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                        cell = self.grid[ny][nx]
                        if cell.owner is not None and cell.owner != faction['id']:
                            is_capital_safe = False
                            break
                if not is_capital_safe:
                    break
            if is_capital_safe:
                faction['hostility'] = min(1.0, faction['hostility'] * HOSTILITY_BONUS) # 최대 1.0으로 제한

        

        for y in range(GRID_SIZE): 
            for x in range(GRID_SIZE):
                cell = self.grid[y][x]
                if cell.owner is not None:
                    self.factions[cell.owner]['territory_count'] += 1
                    self.factions[cell.owner]['total_soldiers'] += cell.soldiers

        for faction in self.factions:
            if faction['is_alive']:
                lake_bonus = 1.1 if self._has_lake_bonus(faction['id']) else 1.0
                production = 0
                for y in range(GRID_SIZE):
                    for x in range(GRID_SIZE):
                        if self.grid[y][x].owner == faction['id']:
                            cell = self.grid[y][x]
                            modifier = TERRAIN_TYPES[cell.terrain]['pop_modifier']
                            production += int(random.randint(1, 3) * modifier * lake_bonus)
                faction['total_population'] += production

        for faction in self.factions:
            if not (faction['is_alive'] and faction['territory_count'] > 0): continue
            if faction['total_soldiers'] >= MAX_SOLDIERS_PER_FACTION: continue
            pop_for_soldiers = int(faction['total_population'] * faction['hostility'])
            new_soldiers = min(pop_for_soldiers // SOLDIER_COST, MAX_SOLDIERS_PER_FACTION - faction['total_soldiers'])
            if new_soldiers > 0:
                faction['total_population'] -= new_soldiers * SOLDIER_COST
                main_territory_cells = faction['main_territory']
                if not main_territory_cells: continue
                for _ in range(new_soldiers):
                    for _ in range(len(main_territory_cells)):
                        x, y = random.choice(list(main_territory_cells))
                        if self.grid[y][x].soldiers < MAX_SOLDIERS_PER_CELL:
                            self.grid[y][x].soldiers += 1
                            break
        
        self._redeploy_soldiers()
        for faction in self.factions:
            if not faction['is_alive']: continue
            self._faction_action(faction)
        self._write_log()

    def _reassign_ai_traits(self):
        # Reset all traits first
        for faction in self.factions:
            faction['ai_trait'] = None
        
        # Assign new traits, ensuring only one defender
        available_traits_for_assignment = list(AI_TRAITS)
        defender_assigned_this_cycle = False
        
        # Special case for turn 500: largest faction gets 20% chance to be defender
        if self.turn == 500:
            alive_factions = [f for f in self.factions if f['is_alive']]
            if alive_factions:
                largest_territory_faction = max(alive_factions, key=lambda f: f['territory_count'])
                if random.random() < 0.2: # 20% chance
                    largest_territory_faction['ai_trait'] = 'defender'
                    defender_assigned_this_cycle = True
                    if 'defender' in available_traits_for_assignment:
                        available_traits_for_assignment.remove('defender')
        
        # Assign traits to remaining factions
        for faction in self.factions:
            if faction['ai_trait'] is None: # Only assign if not already assigned (e.g., defender at turn 500)
                if not defender_assigned_this_cycle:
                    assigned_trait = random.choice(available_traits_for_assignment)
                    if assigned_trait == 'defender':
                        defender_assigned_this_cycle = True
                        available_traits_for_assignment.remove('defender')
                    faction['ai_trait'] = assigned_trait
                else:
                    # If defender is already assigned, ensure no other faction gets it
                    non_defender_traits = [t for t in AI_TRAITS if t != 'defender']
                    faction['ai_trait'] = random.choice(non_defender_traits)

    def _process_captures(self):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell = self.grid[y][x]
                if cell.capturing_faction is not None:
                    cell.capture_timer -= 1
                    if cell.capture_timer <= 0:
                        capturing_faction = self.factions[cell.capturing_faction]
                        if capturing_faction['total_population'] >= self.current_capture_cost:
                            capturing_faction['total_population'] -= self.current_capture_cost
                            original_owner = cell.owner
                            cell.owner = cell.capturing_faction
                            cell.soldiers = 1
                            if original_owner is not None and (x,y) == self.factions[original_owner]['capital_core']:
                                self._absorb_faction(original_owner, cell.owner)
                            elif original_owner is not None and (x,y) in self.factions[original_owner]['capital_zone']:
                                self.factions[original_owner]['vendetta_target'] = cell.owner
                        cell.capturing_faction = None

    def _absorb_faction(self, defeated_id, victor_id):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x].owner == defeated_id:
                    self.grid[y][x].owner = victor_id
        self.factions[defeated_id]['is_alive'] = False

    def _has_lake_bonus(self, faction_id):
        count = sum(1 for x,y in self.lake_perimeter if self.grid[y][x].owner == faction_id)
        return count / len(self.lake_perimeter) >= 0.6 if self.lake_perimeter else False

    def _find_territory_groups(self, all_owned_cells):
        visited, groups = set(), []
        for x, y in all_owned_cells:
            if (x, y) not in visited:
                current_group, q = set(), deque([(x, y)])
                visited.add((x, y)); current_group.add((x, y))
                while q:
                    cx, cy = q.popleft()
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) in all_owned_cells and (nx, ny) not in visited:
                            visited.add((nx, ny)); current_group.add((nx, ny)); q.append((nx, ny))
                groups.append(current_group)
        return groups

    def _redeploy_soldiers(self):
        for faction in self.factions:
            if not faction['is_alive']: continue
            if self.turn > EARLY_GAME_TURNS:
                capital_cells = faction['capital_zone']
                capital_soldiers = sum(self.grid[y][x].soldiers for x,y in capital_cells)
                required_defense = int(faction['total_soldiers'] * CAPITAL_DEFENSE_RATIO)
                if capital_soldiers < required_defense and faction['total_soldiers'] > 10:
                    needed = required_defense - capital_soldiers
                    # ... (이전과 동일한 방어 병력 충원 로직)
            
            border_cells = {cell for cell in faction['main_territory'] if self._is_border_cell(cell[0], cell[1], faction['id'])}
            inner_cells = faction['main_territory'] - border_cells
            if self.turn > EARLY_GAME_TURNS: inner_cells -= faction['capital_zone']

            if not border_cells: continue
            for x, y in inner_cells:
                if self.grid[y][x].soldiers > 0:
                    tx, ty = random.choice(list(border_cells))
                    self.grid[ty][tx].soldiers = min(self.grid[ty][tx].soldiers + self.grid[y][x].soldiers, MAX_SOLDIERS_PER_CELL)
                    self.grid[y][x].soldiers = 0

    def _is_border_cell(self, x, y, faction_id):
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE) or self.grid[ny][nx].owner != faction_id:
                return True
        return False

    def _faction_action(self, faction):
        # Vendetta target has highest priority
        if faction['vendetta_target'] is not None:
            targets = self._find_adjacent_cells(faction['id'], owner_type='enemy', specific_enemy=faction['vendetta_target'])
            if not targets:
                faction['vendetta_target'] = None
            else:
                for x,y,nx,ny in targets:
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_ATTACK:
                        self._start_capture(x, y, nx, ny)
                return

        # Early game: prioritize expansion
        if self.turn <= EXPANSION_PRIORITY_TURNS:
            targets = self._find_adjacent_cells(faction['id'], owner_type='empty')
            if targets:
                x,y,nx,ny = random.choice(targets)
                if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_CAPTURE_EMPTY:
                    self._start_capture(x, y, nx, ny)
                return
            # If no empty cells, try to attack enemies
            targets = self._find_adjacent_cells(faction['id'], owner_type='enemy')
            if targets:
                x,y,nx,ny = random.choice(targets)
                if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_ATTACK:
                    self._start_capture(x, y, nx, ny)
                return

        # Late game: AI trait based actions
        else:
            if faction['ai_trait'] == 'expansionist':
                targets = self._find_adjacent_cells(faction['id'], owner_type='empty')
                if targets:
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_CAPTURE_EMPTY:
                        self._start_capture(x, y, nx, ny)
                    return
                # If no empty cells, try to attack enemies
                targets = self._find_adjacent_cells(faction['id'], owner_type='enemy')
                if targets:
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_ATTACK:
                        self._start_capture(x, y, nx, ny)
                    return

            elif faction['ai_trait'] == 'conqueror':
                targets = self._find_adjacent_cells(faction['id'], owner_type='enemy')
                if targets:
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_ATTACK:
                        self._start_capture(x, y, nx, ny)
                    return
                # If no enemy cells, try to expand into empty cells
                targets = self._find_adjacent_cells(faction['id'], owner_type='empty')
                if targets:
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_CAPTURE_EMPTY:
                        self._start_capture(x, y, nx, ny)
                    return

            elif faction['ai_trait'] == 'defender':
                # Defenders are less aggressive, primarily focus on defense (handled by _redeploy_soldiers)
                # They might still expand into empty cells if very safe
                targets = self._find_adjacent_cells(faction['id'], owner_type='empty')
                if targets and random.random() < 0.5: # 50% chance to expand if safe
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_CAPTURE_EMPTY:
                        self._start_capture(x, y, nx, ny)
                    return
                # If no empty cells or didn't expand, try to attack nearby weak enemies
                targets = self._find_adjacent_cells(faction['id'], owner_type='enemy')
                if targets and random.random() < 0.2: # Lower chance to attack enemies
                    x,y,nx,ny = random.choice(targets)
                    if self.grid[y][x].soldiers >= MIN_SOLDIERS_TO_ATTACK:
                        self._start_capture(x, y, nx, ny)
                    return

    def _find_adjacent_cells(self, faction_id, owner_type='any', specific_enemy=None):
        targets = []
        for x, y in self._get_border_cells(faction_id):
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and self.grid[ny][nx].terrain != 'lake' and self.grid[ny][nx].capturing_faction is None:
                    neighbor = self.grid[ny][nx]
                    if owner_type == 'empty':
                        if neighbor.owner is None:
                            targets.append((x, y, nx, ny))
                    elif owner_type == 'enemy':
                        if neighbor.owner is not None and neighbor.owner != faction_id:
                            if specific_enemy is None or neighbor.owner == specific_enemy:
                                targets.append((x, y, nx, ny))
                    elif owner_type == 'any': # This covers both empty and enemy cells
                        if neighbor.owner != faction_id:
                            targets.append((x, y, nx, ny))
        return targets

    def _get_border_cells(self, faction_id):
        return {cell for cell in self.factions[faction_id]['main_territory'] if self._is_border_cell(cell[0], cell[1], faction_id)}

    def _start_capture(self, x, y, nx, ny):
        cell = self.grid[y][x]
        neighbor = self.grid[ny][nx]
        required_soldiers = MIN_SOLDIERS_TO_CAPTURE_EMPTY if neighbor.owner is None else MIN_SOLDIERS_TO_ATTACK
        if cell.soldiers < required_soldiers: return

        if neighbor.owner is not None:
            force = random.randint(5, 10)
            if cell.soldiers < force: force = cell.soldiers
            cell.soldiers -= force
            atk_power = force ** 2
            def_power = neighbor.soldiers ** 2
            
            # 산악 지형 방어 보너스 적용
            if neighbor.terrain == 'mountain':
                def_power *= MOUNTAIN_DEFENSE_BONUS

            if (atk_power + def_power) > 0 and random.random() < atk_power / (atk_power + def_power):
                neighbor.soldiers = 0
                cell.soldiers += int(force * ATTACK_SURVIVOR_RATIO)
            else:
                return

        neighbor.capturing_faction = cell.owner
        neighbor.capture_timer = TERRAIN_TYPES[neighbor.terrain]['capture_time']

    def _check_game_over(self):
        alive_factions = [f for f in self.factions if f['is_alive']]
        if len(alive_factions) <= 1:
            self.game_over = True
            self.winner = f"Faction {alive_factions[0]['id'] + 1}" if alive_factions else "No one"
            self.log_file.write(f"Game Over. Winner: {self.winner}\n")
        elif self.turn >= MAX_TURNS:
            self.game_over = True
            winner_faction = max([f for f in self.factions if f['is_alive']], key=lambda f: f['territory_count'])
            self.winner = f"Faction {winner_faction['id'] + 1} (Time Over)"
            self.log_file.write(f"Game Over. Winner: {self.winner}\n")

    def _draw(self):
        self.screen.fill(PANEL_BG)
        self._draw_grid()
        self._draw_info_panel()
        if self.game_over: self._draw_game_over()
        pygame.display.flip()

    def _draw_grid(self):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                cell = self.grid[y][x]
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if cell.owner is not None:
                    color = self.factions[cell.owner]['color']
                    brightness = min(150, cell.soldiers * 5)
                    final_color = tuple(max(0, c - brightness) for c in color)
                    pygame.draw.rect(self.screen, final_color, rect)
                    if (x,y) in self.factions[cell.owner]['capital_zone']:
                        pygame.draw.rect(self.screen, (255,215,0), rect, 1)
                    if cell.soldiers > 0:
                        pygame.draw.circle(self.screen, BLACK, rect.center, 2)
                else:
                    terrain_color = TERRAIN_TYPES[cell.terrain]['color']
                    pygame.draw.rect(self.screen, terrain_color, rect)
                if cell.capturing_faction is not None:
                    progress = 1 - (cell.capture_timer / TERRAIN_TYPES[cell.terrain]['capture_time'])
                    pygame.draw.line(self.screen, FACTION_COLORS[cell.capturing_faction], rect.bottomleft, (rect.left + rect.width * progress, rect.bottom), 2)

    def _draw_info_panel(self):
        panel_x = GRID_SIZE * CELL_SIZE
        turn_text = self.font.render(f"Turn: {self.turn} / {MAX_TURNS}", True, WHITE)
        capture_cost_text = self.font.render(f"Capture Cost: {self.current_capture_cost:,}", True, WHITE)
        self.screen.blit(turn_text, (panel_x + 10, 10))
        self.screen.blit(capture_cost_text, (panel_x + 10, 30))
        y_offset = 60
        for faction in self.factions:
            color_rect = pygame.Rect(panel_x + 10, y_offset, 20, 20)
            pygame.draw.rect(self.screen, faction['color'], color_rect)
            name = f"Faction {faction['id'] + 1}"
            if not faction['is_alive']: name += " (Defeated)"
            pop_text = f" Pop: {faction['total_population']:,}"
            sol_text = f" Sol: {faction['total_soldiers']:,} / {MAX_SOLDIERS_PER_FACTION}"
            ter_text = f" Ter: {faction['territory_count']}"
            hos_text = f" Hostility: {faction['hostility']:.2f} ({faction['ai_trait']})"
            self.screen.blit(self.font.render(name, True, WHITE), (panel_x + 40, y_offset))
            self.screen.blit(self.font.render(pop_text, True, WHITE), (panel_x + 40, y_offset + 20))
            self.screen.blit(self.font.render(sol_text, True, WHITE), (panel_x + 40, y_offset + 40))
            self.screen.blit(self.font.render(ter_text, True, WHITE), (panel_x + 40, y_offset + 60))
            if faction['is_alive']:
                self.screen.blit(self.font.render(hos_text, True, WHITE), (panel_x + 40, y_offset + 80))
            y_offset += 110
        y_offset += 20
        legend_title = self.font.render("Terrain Legend:", True, WHITE)
        self.screen.blit(legend_title, (panel_x + 10, y_offset))
        y_offset += 25
        for terrain_type, data in TERRAIN_TYPES.items():
            if data['capture_time'] == -1: continue
            pygame.draw.rect(self.screen, data['color'], (panel_x + 10, y_offset, 15, 15))
            text = self.small_font.render(f"{data['name']} ({data['capture_time']}T)", True, WHITE)
            self.screen.blit(text, (panel_x + 30, y_offset))
            y_offset += 20

    def _draw_game_over(self):
        # ... (이전과 동일)
        pass

    def run(self):
        try:
            while True:
                self._handle_input()
                if not self.game_over:
                    self._update_game_state()
                    self._check_game_over()
                self._draw()
                self.clock.tick(FPS)
        finally:
            if self.log_file:
                self.log_file.close()
            pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()
