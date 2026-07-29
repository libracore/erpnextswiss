# -*- coding: utf-8 -*-
#
# worktime_utils.py
#
# Copyright (C) libracore, 2026
# https://www.libracore.com or https://github.com/libracore

import frappe
from frappe.utils import getdate, add_days, flt
from datetime import datetime, time

"""
Hauptmethode
"""
def get_worktime_overview(employee, company, from_date, to_date):
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    target_time = get_target_time(employee, company, from_date, to_date)
    actual_time = get_actual_time(employee, company, from_date, to_date)
    holidays_in_hours = get_holidays_in_hours(employee, company, from_date, to_date)
    overtime = get_overtime(target_time, actual_time, holidays_in_hours)
    opening_balance = get_opening_balance(employee, company, from_date)
    closing_balance = get_closing_balance(employee, company, to_date)
    holiday_hours_check = {}
    vacation_hours_based_on = frappe.db.get_value("Worktime Settings", "Worktime Settings", "vacation_hours_based_on")

    if vacation_hours_based_on == "Timesheet":
        holiday_hours_check = check_holiday_hours(employee, company, from_date, to_date)

    return {
        "target_time": target_time,
        "actual_time": actual_time,
        "holidays_in_hours": holidays_in_hours,
        "overtime": overtime,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "holiday_hours_check": holiday_hours_check
    }


"""
Hilfsmethoden
"""
def get_target_time(employee, company, from_date, to_date):
    '''
        Diese Methode liefert die SOLL-Zeit in Stunden.

        Wenn ein Tag aus dem Datumsbereich in einer gültigen
        Holiday-List vorkommt, wird dieser mit 0 SOLL-Stunden
        berechnet.
    '''
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    target_daily_hours = get_daily_hours(company)
    target_time_in_hours = 0.0
    days_off = set(get_days_off(company, from_date, to_date))
    days = (to_date - from_date).days + 1

    for i in range(days):
        current_date = add_days(from_date, i)

        if current_date in days_off:
            # Überspringen wenn der Tag ein Feiertag/Wochenende ist.
            # Wochenende müssen in der Holidaylist erfasst sein.
            continue

        fte = get_fte_on_date(employee, current_date)
        target_time_in_hours += target_daily_hours * fte

    return target_time_in_hours


def get_actual_time(employee, company, from_date, to_date):
    '''
        Diese Methode liefert die IST-Zeit in Stunden.

        Wenn in den Worktime Settings
        vacation_hours_based_on = Timesheet ist,
        werden alle IST-Stunden, welche zu einem Activity Type
        vorkommend in der Tabelle Activity Type Determination gehören,
        ausgenommen.
    '''
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    range_start = "{} 00:00:00".format(from_date)
    range_end = "{} 00:00:00".format(add_days(to_date, 1))
    vacation_hours_based_on = frappe.db.get_value("Worktime Settings", "Worktime Settings", "vacation_hours_based_on")
    excluded_activity_types = []

    if vacation_hours_based_on == "Timesheet":
        excluded_activity_types = frappe.db.sql_list("""
            SELECT DISTINCT
                `activity_type`
            FROM
                `tabActivity Type Determination`
            WHERE
                `company` = %(company)s
                AND `activity_type` IS NOT NULL
                AND `activity_type` != ''
        """, {
            "company": company
        })

    activity_type_condition = ""

    if excluded_activity_types:
        activity_type_condition = """
            AND (
                `detail`.`activity_type` IS NULL
                OR `detail`.`activity_type` NOT IN %(excluded_activity_types)s
            )
        """

    result = frappe.db.sql("""
        SELECT
            SUM(
                TIMESTAMPDIFF(
                    SECOND,
                    GREATEST(`detail`.`from_time`, %(range_start)s),
                    LEAST(`detail`.`to_time`, %(range_end)s)
                )
            ) / 3600 AS `actual_hours`
        FROM
            `tabTimesheet Detail` AS `detail`
        INNER JOIN
            `tabTimesheet` AS `timesheet`
            ON `timesheet`.`name` = `detail`.`parent`
        WHERE
            `detail`.`parenttype` = 'Timesheet'
            AND `timesheet`.`company` = %(company)s
            AND `timesheet`.`employee` = %(employee)s
            AND `timesheet`.`docstatus` = 1
            AND `detail`.`from_time` < %(range_end)s
            AND `detail`.`to_time` > %(range_start)s
            {activity_type_condition}
    """.format(
        activity_type_condition=activity_type_condition
    ), {
        "company": company,
        "employee": employee,
        "range_start": range_start,
        "range_end": range_end,
        "excluded_activity_types": tuple(excluded_activity_types)
    }, as_dict=True)

    if not result or result[0].actual_hours is None:
        return 0.0

    return flt(result[0].actual_hours)


def get_holidays_in_hours(employee, company, from_date, to_date):
    '''
        Diese Methode liefert die Ferien-/Abwesenheitsstunden.

        Bei vacation_hours_based_on = Timesheet:
            Berücksichtigt werden alle Timesheet Details, deren
            Activity Type in der Tabelle Activity Type Determination
            für die entsprechende Firma vorkommt.

        Bei vacation_hours_based_on = Leave Application:
            Berücksichtigt werden alle genehmigten Leave Applications
            des Mitarbeiters, die den abgefragten Zeitraum vollständig
            oder teilweise überschneiden.

            Ganze Urlaubstage werden mit dem individuellen Tagessoll
            berechnet:
                tägliche Arbeitszeit * Beschäftigungsgrad

            Der in half_day_date definierte Halbtag wird mit 50 %
            des individuellen Tagessolls berechnet.

            Arbeitsfreie Tage aus der Holiday List werden nicht als
            Urlaubsstunden berücksichtigt.
    '''
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    vacation_hours_based_on = frappe.db.get_value("Worktime Settings", "Worktime Settings", "vacation_hours_based_on")

    if vacation_hours_based_on == "Timesheet":
        included_activity_types = frappe.db.sql_list("""
            SELECT DISTINCT
                `activity_type`
            FROM
                `tabActivity Type Determination`
            WHERE
                `company` = %(company)s
                AND `activity_type` IS NOT NULL
                AND `activity_type` != ''
        """, {
            "company": company
        })

        if not included_activity_types:
            return 0.0

        range_start = "{} 00:00:00".format(from_date)
        range_end = "{} 00:00:00".format(add_days(to_date, 1))

        result = frappe.db.sql("""
            SELECT
                SUM(
                    TIMESTAMPDIFF(
                        SECOND,
                        GREATEST(
                            `detail`.`from_time`,
                            %(range_start)s
                        ),
                        LEAST(
                            `detail`.`to_time`,
                            %(range_end)s
                        )
                    )
                ) / 3600 AS `holiday_hours`
            FROM
                `tabTimesheet Detail` AS `detail`
            INNER JOIN
                `tabTimesheet` AS `timesheet`
                ON `timesheet`.`name` = `detail`.`parent`
            WHERE
                `detail`.`parenttype` = 'Timesheet'
                AND `timesheet`.`company` = %(company)s
                AND `timesheet`.`employee` = %(employee)s
                AND `timesheet`.`docstatus` = 1
                AND `detail`.`activity_type`
                    IN %(included_activity_types)s
                AND `detail`.`from_time` < %(range_end)s
                AND `detail`.`to_time` > %(range_start)s
        """, {
            "company": company,
            "employee": employee,
            "range_start": range_start,
            "range_end": range_end,
            "included_activity_types": tuple(
                included_activity_types
            )
        }, as_dict=True)

        if not result or result[0].holiday_hours is None:
            return 0.0

        return flt(result[0].holiday_hours)

    if vacation_hours_based_on == "Leave Application":
        leave_applications = frappe.db.sql("""
            SELECT
                `name`,
                `from_date`,
                `to_date`,
                `half_day`,
                `half_day_date`
            FROM
                `tabLeave Application`
            WHERE
                `employee` = %(employee)s
                AND `company` = %(company)s
                AND `docstatus` = 1
                AND `status` = 'Approved'
                AND `from_date` <= %(to_date)s
                AND `to_date` >= %(from_date)s
            ORDER BY
                `from_date` ASC,
                `to_date` ASC
        """, {
            "employee": employee,
            "company": company,
            "from_date": from_date,
            "to_date": to_date
        }, as_dict=True)

        if not leave_applications:
            return 0.0

        target_daily_hours = get_daily_hours(company)
        days_off = set(get_days_off(company, from_date, to_date))
        holiday_hours = 0.0

        for leave_application in leave_applications:
            leave_from_date = getdate(leave_application.from_date)
            leave_to_date = getdate(leave_application.to_date)
            effective_from_date = max(leave_from_date, from_date)
            effective_to_date = min(leave_to_date, to_date)
            half_day_date = None

            if (leave_application.half_day and leave_application.half_day_date):
                half_day_date = getdate(leave_application.half_day_date)

            number_of_days = (effective_to_date - effective_from_date).days + 1

            for i in range(number_of_days):
                current_date = add_days(effective_from_date, i)

                if current_date in days_off:
                    continue

                fte = get_fte_on_date(employee, current_date)
                daily_hours = (target_daily_hours * fte)

                if leave_application.half_day:
                    if half_day_date:
                        is_half_day = half_day_date == current_date
                    else:
                        is_half_day = (
                            leave_from_date == leave_to_date
                            and current_date == leave_from_date
                        )

                    if is_half_day:
                        daily_hours *= 0.5

                holiday_hours += daily_hours

        return flt(holiday_hours)

    return 0.0


def check_holiday_hours(employee, company, from_date, to_date):
    '''
        Plausibilisiert die erfassten Ferien-/Abwesenheitsstunden.

        Pro Arbeitstag sind ausschliesslich folgende Werte gültig:
            halber Ferientag = tägliche Arbeitszeit * Pensum * 0.5
            ganzer Ferientag = tägliche Arbeitszeit * Pensum

        Ein Timesheet Detail wird vollständig dem Datum seines effektiven
        Beginns zugeordnet. Es wird nicht an Mitternacht auf mehrere Tage
        aufgeteilt.

        Liegt der Beginn vor dem abgefragten Zeitraum, wird der Eintrag
        auf den Beginn des abgefragten Zeitraums begrenzt.

        Die Abweichung wird wie folgt ausgewiesen:
        - Erfasste Stunden kleiner als ein halber Tag:
          Differenz zum halben Tag.
        - Erfasste Stunden zwischen einem halben und einem ganzen Tag:
          Bereich zwischen der Abweichung zum halben und zum ganzen Tag.
        - Erfasste Stunden grösser als ein ganzer Tag:
          Differenz zum ganzen Tag.
    '''
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    empty_result = {
        "days": [],
        "summary": {
            "number_of_days": 0,
            "number_of_valid_days": 0,
            "number_of_invalid_days": 0,
            "recorded_hours": 0.0,
            "deviation_hours": {
                "min": 0.0,
                "max": 0.0
            }
        }
    }

    vacation_hours_based_on = frappe.db.get_value("Worktime Settings", "Worktime Settings", "vacation_hours_based_on")

    if vacation_hours_based_on != "Timesheet":
        return empty_result

    included_activity_types = frappe.db.sql_list("""
        SELECT DISTINCT
            `activity_type`
        FROM
            `tabActivity Type Determination`
        WHERE
            `company` = %(company)s
            AND `activity_type` IS NOT NULL
            AND `activity_type` != ''
    """, {
        "company": company
    })

    if not included_activity_types:
        return empty_result

    range_start = datetime.combine(from_date, time.min)
    range_end = datetime.combine(add_days(to_date, 1), time.min)

    entries = frappe.db.sql("""
        SELECT
            `detail`.`from_time`,
            `detail`.`to_time`
        FROM
            `tabTimesheet Detail` AS `detail`
        INNER JOIN
            `tabTimesheet` AS `timesheet`
            ON `timesheet`.`name` = `detail`.`parent`
        WHERE
            `detail`.`parenttype` = 'Timesheet'
            AND `timesheet`.`company` = %(company)s
            AND `timesheet`.`employee` = %(employee)s
            AND `timesheet`.`docstatus` = 1
            AND `detail`.`activity_type`
                IN %(included_activity_types)s
            AND `detail`.`from_time` < %(range_end)s
            AND `detail`.`to_time` > %(range_start)s
        ORDER BY
            `detail`.`from_time` ASC
    """, {
        "company": company,
        "employee": employee,
        "range_start": range_start,
        "range_end": range_end,
        "included_activity_types": tuple(
            included_activity_types
        )
    }, as_dict=True)

    holiday_hours_by_date = {}

    for entry in entries:
        # Den Eintrag auf den abgefragten Zeitraum begrenzen
        entry_start = max(entry.from_time, range_start)
        entry_end = min(entry.to_time, range_end)

        if entry_end <= entry_start:
            continue

        hours = (entry_end - entry_start).total_seconds() / 3600.0

        # Der komplette Eintrag dem Datum seines effektiven Beginns zuordnen, keine Aufteilung an Mitternacht
        holiday_date = entry_start.date()
        holiday_hours_by_date[holiday_date] = (holiday_hours_by_date.get(holiday_date, 0.0) + hours)

    target_daily_hours = get_daily_hours(company)
    days_off = set(get_days_off(company, from_date, to_date))
    tolerance = 0.02 # Rundungstoleranz von ungefähr 1.2 Minuten
    day_results = []

    summary = {
        "number_of_days": 0,
        "number_of_valid_days": 0,
        "number_of_invalid_days": 0,
        "recorded_hours": 0.0,
        "deviation_hours": {
            "min": 0.0,
            "max": 0.0
        }
    }

    for holiday_date, recorded_hours in sorted(holiday_hours_by_date.items()):
        is_day_off = holiday_date in days_off
        fte = get_fte_on_date(employee, holiday_date)
        personal_daily_hours = (target_daily_hours * fte)
        half_day_hours = (personal_daily_hours * 0.5)
        full_day_hours = personal_daily_hours
        holiday_fraction = None

        if is_day_off:
            is_valid = recorded_hours <= tolerance

            deviation_min = max(recorded_hours, 0.0)
            deviation_max = deviation_min

            if is_valid:
                holiday_fraction = 0.0

        else:
            half_day_deviation = abs(recorded_hours - half_day_hours)
            full_day_deviation = abs(recorded_hours - full_day_hours)
            is_half_day = (half_day_deviation <= tolerance)
            is_full_day = (full_day_deviation <= tolerance)
            is_valid = (is_half_day or is_full_day)

            if is_half_day:
                holiday_fraction = 0.5

            elif is_full_day:
                holiday_fraction = 1.0

            if recorded_hours < half_day_hours:
                deviation_min = (half_day_hours - recorded_hours)
                deviation_max = deviation_min

            elif recorded_hours > full_day_hours:
                deviation_min = (recorded_hours - full_day_hours)
                deviation_max = deviation_min

            else:
                deviation_to_half_day = (recorded_hours - half_day_hours)
                deviation_to_full_day = (full_day_hours - recorded_hours)
                deviation_min = min(deviation_to_half_day, deviation_to_full_day)
                deviation_max = max(deviation_to_half_day, deviation_to_full_day)

        day_results.append({
            "date": holiday_date,
            "fte": flt(fte),
            "is_day_off": is_day_off,
            "personal_daily_hours": flt(personal_daily_hours),
            "half_day_hours": flt(half_day_hours),
            "full_day_hours": flt(full_day_hours),
            "recorded_hours": flt(recorded_hours),
            "holiday_fraction": (flt(holiday_fraction) if holiday_fraction is not None else None),
            "deviation_hours": {
                "min": flt(deviation_min),
                "max": flt(deviation_max)
            },
            "is_valid": is_valid
        })

        summary["number_of_days"] += 1
        summary["recorded_hours"] += recorded_hours

        if is_valid:
            summary["number_of_valid_days"] += 1

        else:
            summary["number_of_invalid_days"] += 1
            summary["deviation_hours"]["min"] += (deviation_min)
            summary["deviation_hours"]["max"] += (deviation_max)

    summary["recorded_hours"] = flt(summary["recorded_hours"])
    summary["deviation_hours"]["min"] = flt(summary["deviation_hours"]["min"])
    summary["deviation_hours"]["max"] = flt(summary["deviation_hours"]["max"])

    return {
        "days": day_results,
        "summary": summary
    }


def get_fte_on_date(employee, date):
    date = getdate(date)

    result = frappe.db.sql("""
        SELECT
            `degree`
        FROM
            `tabEmployment Degree`
        WHERE
            `parent` = %(employee)s
            AND `date` <= %(date)s
            AND `parenttype` = 'Employee'
        ORDER BY
            `date` DESC
        LIMIT 1
    """, {
        "employee": employee,
        "date": date
    }, as_dict=True)

    if not result:
        return 1.0

    return flt(result[0].degree) / 100.0


def get_daily_hours(company):
    result = frappe.db.sql("""
        SELECT
            `daily_hours`
        FROM
            `tabDaily Hours`
        WHERE
            `company` = %(company)s
            AND `parenttype` = 'Worktime Settings'
        LIMIT 1
    """, {
        "company": company
    }, as_dict=True)

    if not result:
        return 8.0

    return flt(result[0].daily_hours)

def get_days_off(company, from_date, to_date):
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if from_date > to_date:
        frappe.throw("Das Startdatum darf nicht nach dem Enddatum liegen.")

    holidays = frappe.db.sql("""
        SELECT
            `holiday_date`
        FROM
            `tabHoliday`
        WHERE
            `parenttype` = 'Holiday List'
            AND `holiday_date` BETWEEN %(from_date)s AND %(to_date)s
            AND `parent` IN (
                SELECT `public_holiday_list`
                FROM `tabPublic Holiday List`
                WHERE `company` = %(company)s
            )
        ORDER BY
            `holiday_date` ASC
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "company": company
    }, as_dict=True)

    return [getdate(holiday.holiday_date) for holiday in holidays]


def get_overtime(target_time, actual_time, holiday_hours):
    return flt(flt(actual_time) + flt(holiday_hours)) - flt(target_time)


def get_stored_carry_over(employee, year):
    '''
        Liefert den in der Child Table gespeicherten Carryover eines
        Mitarbeiters für ein bestimmtes Jahr

        Der Wert gilt jeweils per 1. Januar 00:00 Uhr des Jahres
    '''
    amount = frappe.db.sql("""
        SELECT
            SUM(`amount`)
        FROM
            `tabCarryover and Payouts`
        WHERE
            `parent` = %(employee)s
            AND `parenttype` = 'Employee'
            AND `year` = %(year)s
    """, {
        "employee": employee,
        "year": int(year)
    })[0][0]

    return flt(amount)

def get_opening_balance(employee, company, from_date):
    '''
        Liefert das Gleitzeitsaldo unmittelbar vor dem Beginn des
        angegebenen Datums

        Beispiel:
            from_date = 2026-06-01
            Ergebnis = Carryover per 01.01.2026 + Gleitzeit vom 01.01.2026 bis 31.05.2026

        Beginnt die Abfrage am 1. Januar, entspricht der Startsaldo
        dem gespeicherten Carryover dieses Jahres
    '''
    from_date = getdate(from_date)
    year_start = getdate("{0}-01-01".format(from_date.year))
    opening_balance = get_stored_carry_over(employee, from_date.year)

    if from_date == year_start:
        return flt(opening_balance)

    previous_day = add_days(from_date, -1)
    target_time = get_target_time(employee, company, year_start, previous_day)
    actual_time = get_actual_time(employee, company, year_start, previous_day)
    holiday_hours = get_holidays_in_hours(employee, company, year_start, previous_day)
    accrued_overtime = get_overtime(target_time, actual_time, holiday_hours)

    return flt(opening_balance + accrued_overtime)

def get_closing_balance(employee, company, to_date):
    '''
        Liefert das Gleitzeitsaldo am Ende des angegebenen Tages

        Beispiel:
            to_date = 2026-06-30
            Ergebnis = Carryover per 01.01.2026 + Gleitzeit vom 01.01.2026 bis 30.06.2026
    '''
    to_date = getdate(to_date)
    year_start = getdate("{0}-01-01".format(to_date.year))
    opening_balance = get_stored_carry_over(employee, to_date.year)
    target_time = get_target_time(employee, company, year_start, to_date)
    actual_time = get_actual_time(employee, company, year_start, to_date)
    holiday_hours = get_holidays_in_hours(employee, company, year_start, to_date)
    accrued_overtime = get_overtime(target_time, actual_time, holiday_hours)

    return flt(opening_balance + accrued_overtime)