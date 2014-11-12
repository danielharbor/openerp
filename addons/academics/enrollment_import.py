import csv
import psycopg2
from datetime import date

conn_string = "dbname='aun' user='openerp' password='OpenErpAdmin001'"

conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

# reader = csv.reader(open('mycsv.csv','rb'))

enr_statement = "select section_id, student_id from aun_registrar_enrollment"
cursor.execute(enr_statement)
conn.commit()
enr_info = cursor.fetchall()

for enr in enr_info:
    l_statement = "SELECT id,level_id,term_id from aun_registrar_section where id='%s'" %enr[0]
    s_statement = "SELECT id,student_state_id from res_partner where id='%s'" %enr[1]
    cursor.execute(l_statement)
    conn.commit()
    section_info = cursor.fetchone()
    cursor.execute(s_statement)
    conn.commit()
    student_info = cursor.fetchone()
    
    lg_statement = "SELECT id from level_gpa where student_id='%s' and level_id='%s'" %(student_info[0], section_info[1])
    cursor.execute(lg_statement)
    conn.commit()
    level_gpa_id = cursor.fetchone()
     
    if not level_gpa_id:
        lg_create = "INSERT INTO level_gpa (student_id,level_id,student_state_id) VALUES (" + str(student_info[0]) + "," + str(section_info[1]) + "," + str(student_info[1]) + ") Returning id"
        cursor.execute(lg_create)
        conn.commit()
        level_gpa_id = cursor.fetchone()
     
    enr_insert = "update aun_registrar_enrollment set level_gpa_id=%s where student_id=%s and section_id=%s" %(level_gpa_id[0], student_info[0], section_info[0])
    cursor.execute(enr_insert)
    conn.commit()
    gi_insert = "update gpa_info set level_gpa_id=%s where student_id=%s and term_id=%s" %(level_gpa_id[0], student_info[0], section_info[2])
    cursor.execute(gi_insert)
    conn.commit()
    print enr