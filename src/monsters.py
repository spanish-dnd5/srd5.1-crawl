import re
from typing import Dict, List, Tuple, Union

from bs4.element import Tag

from custom_types import Action, LegendaryActions, SpecialAbility
from utils import (extract_damage_text, extract_text_from_parent_tag,
                   extract_text_from_tag, find_index, get_actions)


def extract_name(content: Tag) -> str:
    if content.find('h3'):
        name = content.h3
    elif content.find('h4'):
        name = content.h4
    else:
        name = content.h5
    return name.text.replace('\n', '').strip()


def extract_subtitle_info(content: Tag) -> Tuple[str, str, str, List[str]]:
    subtitle_text: str = content.p.text
    subtitle = subtitle_text.replace('\n', '').split(',')
    alignment = subtitle.pop().strip()
    size_type_info = ','.join(subtitle).strip()
    size_type_list = size_type_info.split(' ')
    tags = []
    match = re.search(r'\((.+?)\)', size_type_info)
    if match:
        details = match.group(1)
        tags += details.split(',')

        size_type_info = size_type_info.replace(match.group(0), '').strip()
        size_type_list = size_type_info.split(' ')
        size = size_type_list.pop().strip()
        type_ = ' '.join(size_type_list).strip()
    elif size_type_list[0] == 'Enjambre':
        type_ = f'{size_type_list[3][0].upper()}{size_type_list[3][1:-1]}'
        type_ = type_.strip()
        size = size_type_list[1].strip()
        tags.append(size_type_list[0].strip())
    else:
        size = size_type_list.pop()
        type_ = ' '.join(size_type_list)

    return alignment, size, type_, tags


def extract_description(content: Tag) -> str:
    p_list = content.find_all('p')
    ac_tag = content.find('b', string=re.compile(r'Clase de Armadura:?\s?'))
    ac_index = find_index(p_list, lambda p: p.b == ac_tag)
    return '\n'.join([p.text.replace('\n', ' ') for p in p_list[1:ac_index]])


def extract_armor_class(content: Tag) -> List[Dict[str, Union[int, str]]]:
    result = []
    ac_text = extract_text_from_parent_tag(content, 'Clase de Armadura')
    acs = ac_text.split(',')

    if len(acs) > 1 and not acs[1][1].strip().isdigit():
        acs = [', '.join(acs)]

    for armor_class in acs:
        armor_class = armor_class.strip()
        type_ = ''
        condition = ''
        ac_array = armor_class.split(' ')

        if len(ac_array) > 1 and ac_array[1][1].isdigit():
            second_ac = ' '.join(ac_array[1:])
            armor_class = armor_class.replace(second_ac, '').strip()
            second_ac = second_ac.replace('(', '').replace(')', '')
            acs.append(second_ac)

        match = re.search(r'\((.+?)\)', armor_class)
        if match:
            type_ = match.group(1).strip()
            armor_class = armor_class.replace(match.group(0), '')

        armor_class, *condition_array = armor_class.split(' ')
        condition = ' '.join(condition_array).strip()
        result.append({
            'amount': int(armor_class),
            'type': type_,
            'condition': condition
        })
    return result


def extract_hit_points(content: Tag) -> Tuple[int, str]:
    search = 'Puntos de golpe'
    hp_text = extract_text_from_parent_tag(content, search)
    if not hp_text:
        hp_text = extract_text_from_tag(content, search, tag='p')
    match = re.search(r'\((.+?)\)', hp_text)
    dice = match.group(1).strip()
    hit_points = hp_text.replace(match.group(0), '').strip()
    return int(hit_points), dice


def extract_speed(content: Tag) -> str:
    speed_text = extract_text_from_parent_tag(content, 'Velocidad')
    match = re.search(r'\((.+?)\)', speed_text)
    special_array = []

    if match:
        special_condition = re.search(r'en forma .+', match.group(1))
        if special_condition:
            speed_text = speed_text.replace(match.group(0), '').strip()
            special_speed = match.group(1).replace(special_condition.group(0),
                                                   '').strip()
            special_array = [
                f'{speed} {special_condition.group(0)}'
                for speed in special_speed.split(', ')
            ]

    speed_array = [
        speed.strip() for speed in speed_text.replace('.', ',').split(', ')
    ]
    speed_array += special_array

    result = {}
    for speed in speed_array:
        speed_splitted = speed.split(' ')
        if not speed_splitted[0][0].isdecimal():
            speed_splitted.append(speed_splitted.pop(0).lower())

        if len(speed_splitted) < 3:
            speed_splitted.append('caminando')

        result[' '.join(speed_splitted[2:])] = int(speed_splitted[0])

    return result


def extract_initiative(content: Tag) -> str:
    row = content.table.find_all('tr')[1].find_all('td')[1]
    mod = re.search(r'(.+)\((.+?)\)', row.text).group(2)
    mod = mod.replace('−', '-').replace('–', '-')
    return int(mod)


def extract_abilities(content: Tag) -> Dict[str, int]:
    rows = content.table.find_all('tr')[1].find_all('td')
    abilities = []
    for row in rows:
        row_text = row.text.replace('\n', ' ')
        ability = re.search(r'(.+)\((.+?)\)', row_text).group(1).strip()
        abilities.append(int(ability))

    result = {
        'strength': abilities[0],
        'dexterity': abilities[1],
        'constitution': abilities[2],
        'intelligence': abilities[3],
        'wisdom': abilities[4],
        'charisma': abilities[5],
    }
    return result


def extract_saving_throws(content: Tag) -> Dict[str, int]:
    throws_text = extract_text_from_parent_tag(content, 'Tiradas de salvación')
    result = {}
    if throws_text:
        throws_array = throws_text.split(',')
        for saving_throw in throws_array:
            match = re.search(r'(\w{3})\s(.+)', saving_throw)
            if match:
                result[match.group(1)] = int(match.group(2))
    return result


def extract_skills(content: Tag) -> Dict[str, int]:
    skills_text = extract_text_from_parent_tag(content, 'Habilidades')
    result = {}
    if skills_text:
        skills_array = skills_text.split(',')
        for skill in skills_array:
            special = re.search(r'\((.+?)\)', skill)
            if special:
                skill = skill.replace(special.group(0), '')

            match = re.search(r'(\w+[\s?\w*]+)\s(.+)', skill)
            if match:
                result[match.group(1)] = int(match.group(2))
                if special:
                    conditional = f'{match.group(1)} {special.group(1)[3:]}'
                    result[conditional] = int(special.group(1)[0:2])
    return result


def extract_vulnerabilities(content: Tag) -> List[str]:
    text = extract_text_from_parent_tag(content, 'Vulnerabilidades al daño')
    return extract_damage_text(text) if text else []


def extract_resistances(content: Tag) -> List[str]:
    text = extract_text_from_parent_tag(content, 'Resistencias al daño')
    return extract_damage_text(text) if text else []


def extract_immunities(content: Tag) -> List[str]:
    text = extract_text_from_parent_tag(content, 'Inmunidades al daño')
    return extract_damage_text(text) if text else []


def extract_condition_immunities(content: Tag) -> List[str]:
    text = extract_text_from_parent_tag(content, 'Inmunidades a estados')
    if text:
        return [text.strip().capitalize() for text in text.split(',')]
    else:
        return []


def extract_senses(content: Tag) -> List[str]:
    text = extract_text_from_parent_tag(content, 'Sentidos')
    if not text:
        p_list = content.find_all('p')
        languages_tag = content.find('b', string=re.compile(r'Idiomas:?\s?'))
        language_index = find_index(p_list, lambda p: p.b == languages_tag) - 1
        text = p_list[language_index].b.parent.text

    return [text.strip().capitalize() for text in text.split(',')]


def extract_languages(content: Tag) -> List[str]:
    languages_text = extract_text_from_parent_tag(content, 'Idiomas')
    if not languages_text:
        p_list = content.find_all('p')
        senses_tag = content.find('b', string=re.compile(r'Sentidos:?\s?'))
        language_index = find_index(p_list, lambda p: p.b == senses_tag) + 1
        languages_text = p_list[language_index].text

    cant_speak = re.search(', pero no puede hablar', languages_text)

    if cant_speak:

        special = languages_text.split(';')
        special_match = None
        if len(special) > 1:
            special_match = re.search('telepatía', special[1])
            languages_text.replace(';', ',')
            languages_text = re.sub(special[0] + ';', '', languages_text)
        result = ['No puede hablar']
        languages_text = re.sub(cant_speak.group(0), '', languages_text)
        languages_text = re.sub('^Entiende', '', languages_text).strip()
        languages_text = re.sub('^entiende', '', languages_text).strip()
        result += [
            'Entiende ' + text.strip().lower()
            for text in re.split(',| y | e ', languages_text) if text != '-'
        ]
        if special_match:
            result.append(special[1].strip().capitalize())

    else:
        result = [
            text.strip().capitalize()
            for text in re.split(',| y | e ', languages_text) if text != '-'
        ]

    if result and result[-1] == 'Pero no lo habla':
        result[-2] = result[-2] + ', pero no lo habla'
        result.pop()

    return result


def extract_challenge_rating(content: Tag) -> str:
    return extract_text_from_parent_tag(content, 'Desafío')


def extract_special_abilities(content: Tag) -> List[SpecialAbility]:
    p_list = content.find_all('p')
    tag = content.find('b', string=re.compile(r'Desafío:?\s?'))
    cr_index = find_index(p_list, lambda p: p.b == tag)
    tag = content.find('b', string=re.compile(r'Acciones:?\s?'))
    actions_index = find_index(p_list, lambda p: p.b == tag)
    if actions_index == cr_index + 1:
        return []

    special_abilities = p_list[cr_index + 1:]

    result = []
    caster = None
    for tag in special_abilities:
        ability = {}
        if len(tag.contents) == 1 and result:
            break
        if tag.i and tag.i.b:
            name = re.sub(r'\.|:$', '', tag.i.text.replace('\n', ' ').strip())
            desc = tag.text.replace(tag.i.text, '').replace('\n', ' ').strip()
            ability = {'name': name, 'description': desc}

            caster = re.search('Lanzamiento de conjuro', tag.i.text)
            if caster:
                ability['spells'] = []

            result.append(ability)

        elif tag.b:
            name = re.sub(r'\.|:$', '', tag.b.text.replace('\n', ' ').strip())
            desc = tag.text.replace(tag.b.text, '').replace('\n', ' ').strip()
            if caster:
                spell = {'name': name, 'description': desc}
                result[-1]['spells'].append(spell)
            else:
                ability = {'name': name, 'description': desc}
                result.append(ability)

        else:
            description = tag.text.replace('\n', ' ').strip()
            result[-1]['description'] += '\n' + description

    return result


def extract_actions(content: Tag) -> List[Dict[str, str]]:
    return get_actions(content, "Acciones")


def extract_reactions(content: Tag) -> List[Action]:
    return get_actions(content, "Reacciones")


def extract_legendary_actions(content: Tag) -> LegendaryActions:
    legendary_actions = get_actions(content, "Acciones legendarias", True)
    if not legendary_actions:
        return {}
    list_, help_ = legendary_actions
    return {"help": help_, "list": list_}
