# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add user email values

Revision ID: a00000000010
Revises: a00000000009
Create Date: 2019-09-20 12:10:02.271248

"""

from alembic import op, context
import os
import pickle
import sys
import re

# Revision identifiers, used by Alembic.
revision = 'a00000000010'
down_revision = 'a00000000009'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0] + '.pickle')

SERVER_DATA = {
    "api.zephycloud.aziugo.com": {
        "TO_REMOVE": [
            "wfdsfgsdfg.dfgdsfdsh",  # Alex dev tests
            "alextestsignupdddd.alextestsignupdddd",  # Alex dev tests
            "fsdfsdfs.sdfsdfsf",  # Alex dev tests
            "alextestsignupd.alextestsignupd",  # Alex dev tests
            "alextestsignup.alextestsignup",  # Alex dev tests
            "mathias.holzer",  # Doublon with mathias.hoelzer
            "jonlopez.de.maturana",  # Doublon with jon.lopez
            "barbara.jimenezdouglas",   # Doublon with barbara.jimenez.douglas
            "valentine.delavillegeorges",  # Doublon with valentine.de.la.villegeorges
            ".nikolay.stolyarov",  # Doublon with nikolay.stolyarov
            "saravanakarthikeyan.neethimani",  # No info and empty
            "bhanu.sunkari",  # No info and empty
            "matthew.clifton.smith",  # No info and empty
            "team.zephy",  # No info and empty
            "nicolas_2.fatras_2",  # No info and empty
            "nicolas_test.fatras_test", # No info and empty
            "angel.perez.martin",  # No info and empty
            "john..callaghan",  # No info and empty
            "paola.israde.burrola",  # No info and empty
            "hari.haran..b.r",  # No info and empty
            "zephyinscription123456.zephyinscription123456",  # Bad login
            "liu.dian", # Already exists in china database
            u"samuel.déal",
            "testalex.testalex",
            "karthik..rammohan",
            "bastien.simoes.vieira"
        ],
        "TO_RENAME": {
            "ahmet..hatipoglu": "ahmet.hatipoglu",
            u"erkan.yılmaz": "erkan.yilmaz",
            u"martin.särchinger": "martin.sarchinger",
        },
        "EMAIL_LIST": {
            "nick.daniil": "ndaniil@access-power.com",
            "theo.reffet": "theo.reffet@outlook.com",
            "karim.fahssis": "insights@meteopole.com",
            "nicolas.fatras": "nicoftrs@gmail.com",
            "johannes.cordes": "Cordes.Johannes@gmail.com",
            "james.lenzi": "james@j-araujo.eng.br",
            "joao.caldas": "joao.caldas@casadosventos.com.br",
            "jompob.waewsak": "jompob_tsu@hotmail.com",
            "jon.lopez": "jon.lopez@suzlon.com",
            "mathias.hoelzer": "m.hoelzer@profec-ventus.com",
            "philippe.alexandre": "philippe.alexandre@compagnieduvent.com",
            "venkat.naren.d": "fake.naren.d@aziugo.com",
            "volkan.ozer": "vozer@renesis.com.tr",
            "volker.riedel": "volkerr38@gmail.com",
            "tristan.clarenc": "tristan.clarenc@aziugo.com",
            "tristan.clarenc.g": "tristan.clarenc.gold@aziugo.com",
            "tristan.clarenc.s": "tristan.clarenc.silver@aziugo.com",
            "tristan.clarenc.b": "tristan.clarenc.bronze@aziugo.com",
            "nikolay.stolyarov": "snv@vtr-engineering.ru",
            "naveenkumar.puli": "naveenkumar.p@greenkogroup.com",
            "sripriyanka.k": "sripriyanka.k@greenkogroup.com",
            "karim.fahssiss": "karim.fahssiss@aziugo.com",
            "shane.holden": "shanewindenergy@gmail.com",
            "andreas.jansen": "a.jansen@profec-ventus.com",
            "naren.dwadasi": "naren.d@greenkogroup.com",
            "olivier.coupiac": "ocoupiac@maiaeolis.fr",
            "kevin.jorissen": "jorissen@amazon.com",
            "subramanian.avudaiappan": "avudaiappan.s@gmail.com",
            "gaurav.srivastava": "gauravsrivastava@tatapower.com",
            "alireza.karbalaee": "ajavan304@gmail.com",
            "ntombi.msutu": "Ntombi@shawenergyltd.com",
            "daniel.averbuch": "daniel.averbuch@ifp.fr",
            "sinead.reilly": "sinead.reilly@esbi.ie",
            "zhan.li": "lyzhan2005@gmail.com",
            "mehmet.orgen": "mehmetorgen@sabanciuniv.edu",
            "musa.kocaman": "musa.kocaman@siemens.com",
            "arda.gunler": "ardagunler@gmail.com",
            "goksel.gungor": "mehmetgoksel.gungor@gmail.com",
            "charlesbrandon.theis": "theis.charles@gmail.com",
            "onder.nalbant": "ondernalbant@hotmail.com",
            "srinivasan.ashokkumar": "srinivasanashokk@gmail.com",
            "haitong.xu": "xht325@gmail.com",
            "jan.borras": "j.borras@ecofys.com",
            "brian.wiley": "brian.wiley@gmail.com",
            "fadhel.nouri": "nouri_fadhel@yahoo.fr",
            "lee.cameron": "Lee.Cameron@res-ltd.com",
            "albert.torres": "albert.torres@ateknea.com",
            "jackson.lord": "jacksonlord@google.com",
            "nicolas.girard": "ngirard@maiaeolis.fr",
            "angus.chang": "anguschg@gmail.com",
            "sandeep.dixit": "sandeepdixit2004@yahoo.com",
            "mert.satir": "mertsatir@gmail.com",
            "paul.collin": "p.collin@epuron.fr",
            "liu.kevin": "liukevin1129@gmail.com",
            "matteo.mana": "matteomana@hotmail.com",
            "onur.kisar": "abdullahonurkisar@gmail.com",
            "nikos.troullinakis": "ntroulli@gmail.com",
            "benoit.bichet": "benoit.bichet@compagnieduvent.com",
            "eric.jeannotte": "eric.jeannotte@edf-en.ca",
            "erion.kuka": "erion.kuka@acwapower.com",
            "giorgio.castro": "giorgio.crasto@gmail.com",
            "sumio.saito": "saito@wincon.jp",
            "pieter.vandriessche": "pvandriessche@gmail.com",
            "mark.runacres": "Mark.Runacres@vub.ac.be",
            "gibson.kersting": "gibson.kersting@eon.com",
            "sara.quintanafreire": "sara.quintana-freire@eon.com",
            "sandra.motamoreno": "sandra.mota-moreno@eon.com",
            "john.bates": "john.bates@eon.com",
            "elisa.vega": "elisa.vega@eon.com",
            "stanislav.fyodorov": "stanislav.fyodorov@ya.ru",
            "mathieu.peron": "peronmmarine@live.fr",
            "hugo.lecomte": "h.lecomte@ventsdunord.fr",
            "emile.dumas": "emile.dumas@meteopole.com",
            "perrine.bugeat": "perrine.bugeat@greensolver.net",
            "anson.chen": "ansonchen.a@gmail.com",
            "alice.ely": "alice.ely@res-group.com",
            "monontsi.nthontho": "monontsi@kwenergy.co.za",
            "gabriele.bedon": "bedon@ecn.nl",
            "thibaut.toussaint": "toussaint@akuoenergy.com",
            "tristan.clarenc.r": "tristan.clarenc.root@aziugo.com",
            "volker.horlacher": "v.horlacher@anemos-jacob.de",
            "rimtaig.lee": "itslee@chol.com",
            "david.sanders": "david.sanders@sancon.com.au",
            "thithi.soe": "	thithisoe81@gmail.com",
            "valentine.de.la.villegeorges": "villegeorges@akuoenergy.com",
            "pedro.alejandre": "vilar@akuoenergy.com",
            "naveen.kumar": "laxminaveen82@gmail.com",
            "mark.coote": "mcoote@assystem.com",
            "julien.vitet": "julien.vitet@laposte.net",
            "julien.senter": "julien.senter@gmail.com",
            "luis.duran": "luis@intermet.es",
            "thibaud.duong": "thibaud.duong@gmail.com",
            "michel.nocture": "michel.nocture@meteopole.com",
            "francecsco.durante": "fds@k2management.com",
            "jeanmichel.durand": "jeanmichel.durand@windvision.com",
            "barbara.jimenez.douglas": "B.Jimenez@dewi.de",
            "leo.pereniguez": "l.pereniguez@sameole.fr",
            "jerry.randall": "jerry@wind-pioneers.com",
            "vardhan.bhavsar": "vardhan81@gmail.com",
            "zhiyu.zhai": "1026731908@qq.com",
            "aziugo.rock": "hr@meteopole.com",
            "shashi.kant": "shashi.kant@ostro.in",
            "theo.guerrecanon": "tguerre@qidodev.eu",
            "fabre.tristan": "Tristan.Fabre@edf-en.com",
            "jamal.adib": "jamal.adib@enercon.de",
            "meltem.goktas": "meltem.goktas@gmail.com",
            "dmitriy.chernov": "chernov_dmitriy90@mail.ru",
            "ralph.haynes": "rhaynes@xzeres.com",
            "olivier.bedotti": "olivier.bedotti@tractebel.engie.com",
            "gregoire.leroy": "gregoire.leroy@3e.eu",
            "jorge.santos": "jorgesantos@skynet.be",
            "dmytro.goncharenko": "dmy.goncharenko@gmail.com",
            "lise.mourre": "Lise.MOURRE@valorem-energie.com",
            "adil.abbasi": "adil_abbasi2009@hotmail.com",
            "sathyajith.mathew": "windbook@gmail.com",
            "osman.kurt": "osman.kurt@outlook.com",
            "richard.pantel": "rpantel@princeton-engineering.com",
            "mihael.plut": "mihael.plut@gmail.com",
            "samet.tuzunoglu": "stuzunoglu@borusan.com",
            "samuel.deal": "samuel.deal@gmail.com",
            "carlos.martinez": "carlosmmencia@gmail.com",
            "philipp.holt": "p.holt@intervent.fr",
            "angele.giuliano": "angele@acrosslimits.com",
            "thibaut.hamm": "thibaut.hamm@aziugo.com",
            "cyril.jost": "cyril.jost@aziugo.com",
            "dimitrios.kokkinopoulos": "d.kokkinopoulos@gmail.com",
            "petros.theodoropoulos": "ptheod@istos-lab.gr",
            "christophe.minier": "christophe.minier2@gmail.com",
            "francois.cauneau": "francois.cauneau@mines-paristech.fr",
            "lucas.bouvignies": "lucas.bouvignies@gmail.com",
            "bresson.jacky": "bresson@univ-perp.fr",
            "achraf.saadaoui": "achraf.saadaoui@uit.ac.ma",
            "daniel.chizhik": "daniel.chizhik@maine.edu",
            "jeanjacques.brault": "jjbrault37@gmail.com",
            "bernd.deckert": "bernd.deckert@ventsdoc.com",
            "carlos.armentadeu": "cardeu@gmail.com",
            "pedro.benito": "pedro.benito@urjc.es",
            "kavitha.sugumar": "kavisivaprakasam@gmail.com",
            "suresh.pillai": "suresh.pillai@suzlon.com",
            "pavan.sai": "pavansai@powericaltd.com",
            "juan.jijon": "judijival@gmail.com",
            "donghyun.kwak": "ngd52.kwak@gmail.com",
            "antonios.papoutsakis": "apapoutsakis@gmail.com",
            "kaan.boratav": "kaanboratav@gmail.com",
            "sudheesh.sureshkumar": "ss@enbreeze.com",
            "jan.dabrowski": "jd@enbreeze.com",
            "aziugotest.aziugotest": "zephyinscriptionyoupl@yopmail.com",
            "ahmet.hatipoglu": "ahmethat@gmail.com",
            "juan.clemente": "jclemente@acciona.com",
            "yass.none": "kedc91@gmail.com",
            "alejandro.sanchez": "asanchezr@acciona.com",
            "testalexxx.testalexxx": "zephyinscription155555558@yopmail.com",
            "susanne.trommen": "info@strommen-eolica.com",
            "testalexxxddd.testalexxxddd": "zephyinscription155555556@yopmail.com",
            "robert.braunbehrens": "robert.braunbehrens@innogy.com",
            "alberto.gil": "agarcia@acwapower.com",
            "kaan.uenal": "ukaan889@gmail.com",
            "byron.walker": "b.walker@3dEnergy.ca",
            "abubakar.ismail": "abubakar.ismail@amrelisteels.com",
            "prabhjyot.zingh": "prabhjyot.singh98@gmail.com",
            "devanand.gorate": "devanand.gorate@egreenpwr.com",
            "ra.ry": "rary2013@yandex.com",
            "zhang.shuai": "zhangshuaibin@outlook.com",
            "daniel.bleich": "danielbleich@gmx.de",
            "tamer.izmail": "tamer_ismail4@yahoo.com",
            "rajarajan.rathinavelu": "mynameisrajan@gmail.com",
            "pierrick.dupont": "pierrickdup.137@gmail.com",
            "amea.cfd": "Mr.tabbakh@gmail.com",
            "itsara.masiri": "iomasiri@gmail.com",
            "rafa.gonzalez": "rafa4everyone@hotmail.com",
            "veeramanikandan.suriyanarayanan": "3dotenergy@gmail.com",
            "henk.vandecappelle": "vdcivens@proximus.be",
            "rafael.gonzalez": "rafaglez.o@hotmail.com",
            "x.y": "yo199017@yahoo.es",
            "wang.zhonghao": "xuanwaking@163.com",
            "nguyen.manh.ha": "hanm@dau.edu.vn",
            "ajith.pillai": "ajith@renewpower.in",
            "chetan.awasthi": "awasthichetan@gmail.com",
            "alexey.petrov": "alexey.petrov@opencascade.com",
            "mikhail.konishchev": "mak@vtr-engineering.ru",
            "achrafu.saadaouiu": "achraf.saadaoui.ge@gmail.com",
            "morteza.sardari": "morteza.sardari@gmail.com",
            "raul.rubio": "rrubio@ascentio.com.ar",
            "kwonwoo.jang": "changfly@postech.ac.kr",
            "woojin.lee": "wj207@postech.ac.kr",
            "vitalii.h": "vintos94@gmail.com",
            "liu.dian": "liudian@ncpe.com.cn",
            "zi.xu": "676596238@qq.com",
            "vitalii.g": "V.gulevets@gmail.com",
            "mohammad.roshan": "moro1381@gmail.com",
            "mario.klaric": "mario.klaric@professio.hr",
            "thomas.ajj": "thomas.ajj@gmx.de",
            "carlos.valenzuela": "cavalen5@uc.cl",
            "dimitrios.cheimarios": "dimitrischeim@gmail.com",
            "erkan.yilmaz": "erkanyi12@gmail.com",
            "elis.gkeli": "elis-fook@hotmail.com",
            "stefan.eichel": "stefan-eichel@gmx.de",
            "goran.ivkovic": "ivkovigoran@gmail.com",
            "ivan.simic": "ivan.simic@energovizija.hr",
            "pao.israde": "paoisrade@gmail.com",
            "raymond.byrne": "raybyrne2004@gmail.com",
            "andrew.good": "andrewraymondgood@gmail.com",
            "velmurugan.karuppiah": "k.velmurugan77@gmail.com",
            "george.katsoulis": "george3543@gmail.com",
            "jonathan.johrden": "jjohrden@nyit.edu",
            "thomas.walter": "supsup@t-online.de",
            "bhuvan.kumar": "bhuvankumarait@yahoo.co.in",
            "humberto.roman": "humorenserio@gmail.com",
            "adam.vaden": "abvaden801@gmail.com",
            "roland.ries": "roland.ries@email.de",
            "st.ta": "stanimir@spinter.net",
            "thomas.pahlke": "t.pahlke@overspeed.de",
            "richard.gardner": "itsupport@greencatrenewables.co.uk",
            "oste.vega": "ostevega@yahoo.es",
            "martin.sarchinger": "msaerchinger@cpc-germania.com",
            "tristan": "tristan@aziugo.com",
            "sam": "samuel@aziugo.com"
        }
    },
    "api.zephycloud.aziugo.cn": {
        "TO_REMOVE": [
            "bin.liu",
            "karim.fahssisb",
            "zhao.pengyu",
            "karim.fahssis.r",
            "cai.yanfeng",
            "cao.changsong",
            "cheng.dianzhong",
            "chen.keren",
            "cui.xiaohai",
            "deng.yukun",
            "hu.rong",
            "jia.xiao",
            "lei.yangna",
            "liang.chang",
            "li.lei",
            "liu.lei",
            "liu.qinghai",
            "liu.wei",
            "luo.yong",
            "mao.lianwang",
            "ma.xiaojun",
            "pan.pei",
            "su.zhiyong",
            "wang.cong",
            "wang.huashuai",
            "wang.jianfei",
            "wang.na",
            "wang.xianyang",
            "wang.yang",
            "wang.zhuonan",
            "wu.haifeng",
            "wu.menghui",
            "yang.fucheng",
            "yang.jian",
            "yang.jingwen",
            "yu.dan",
            "zhang.xiao",
            "zhang.yong",
            "zhu.le"
        ],
        "TO_RENAME": {},
        "EMAIL_LIST": {
            "cheng.sail": "chengfan5566@163.com",
            "chen.xinming": "1236021@163.com",
            "chen.zhenhua": "309292003@qq.com",
            "chen.zhigang": "13764581427@163.com",
            "fujian.dianliyuan": "fake.fujian.dianliyuan@aziugo.com",
            "gong.wei": "gongwei@bece.net.cn",
            "gong.xi": "784591512@qq.com",
            "hb.edi": "whldliu@163.com",
            "huadong.yuan": "fake.huadong.yuan@aziugo.com",
            "jia.taiyu": "13007174619@163.com",
            "kang.lijian": "635208660@qq.com",
            "karim.fahssis.g": "karim.fahssis@aziugo.com",
            "li.li": "fake.li.li@aziugo.com",
            "liu.dian": "liudian@ncpe.com.cn",
            "liu.donghai": "38346631@qq.com",
            "liu.guozhong": "lgz1328@126.com",
            "liu.zhenyang": "liuzy2013@163.com",
            "nian.guo.kui": "nianguokui@jinkenergy.com",
            "ren.huilai": "alai_cool@126.com",
            "sam": "samuel.deal.cn@aziugo.com",
            "song.jun": "sjsj646123@163.com",
            "sun.pei": "sunpei@ncpe.com.cn",
            "su.zhongying": "szhy0720@126.com",
            "teng.lubao": "tenglubao@goldwind.com.cn",
            "tian.run": "liuying@tianrun.cn",
            "tristan": "tristan.clarenc.cn@aziugo.com",
            "wang.jianhua": "746579223@qq.com",
            "wang.kun": "673844073@qq.com",
            "wu.zhongbo": "wuzhongbo@bece.net.cn",
            "xiang.dian": "hu578344563@163.com",
            "yang.yun": "ryangthu@gmail.com",
            "yan.jiansan": "jiansan.yan@upcrenewables.com.cn",
            "yan.jie": "yanjie@ncepu.edu.cn",
            "yuan.zongtao": "505023804@qq.com",
            "zhao.junhua": "zhaojunhua16@163.com",
            "ziqi.hong": "15116356005@163.com",
            "peng.ming": "fake.peng.ming@aziugo.com",
            "wangfei": "fake.wangfei@aziugo.com",
            "zhao.yongfeng": "fake.zhao.yongfeng@aziugo.com",
        }
    },
    "default": {
        "TO_REMOVE": [],
        "TO_RENAME": {},
        "EMAIL_LIST": {
            "tristan": "tristan@aziugo.com",
            "sam": "sam@aziugo.com"
        }
    }
}

def clean_login(input_login):
    return re.sub(r"\.+", ".", re.sub(r"[^a-z.]+", ".", input_login.strip().lower())).strip(".")


def is_email_valid(input_email):
    if len(input_email) <= 7:
        return False
    return re.match(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", input_email) is not None



def upgrade():
    import core.api_util
    import lib.pg_util

    conn = op.get_bind()

    try:
        domain = context.get_context().config.get_main_option("domain")
    except StandardError as e:
        sys.stderr.write(os.linesep + "Warning: "+str(e)+os.linesep)
        sys.stderr.flush()
        domain = None

    if domain is None or domain not in SERVER_DATA.keys():
        domain = "default"

    action_data = SERVER_DATA[domain]
    removed = {
        "users": [],
        "projects": [],
        "projects_history": [],
        "project_files": [],
        "user_accounts": [],
        "jobs": [],
        "meshes": [],
        "calculations": []
    }
    g_db = core.api_util.DatabaseContext.get_conn()
    for login in action_data["TO_REMOVE"]:
        # Save data to remove pickle files for backup restoration
        results = g_db.execute("SELECT id FROM users WHERE login = %s", [login]).fetchall()
        for result in results:
            user_id = result['id']
            removed["users"].append(result)
            projects = g_db.execute("""SELECT id, uid, user_id, status, data, storage 
                                         FROM projects 
                                        WHERE user_id = %s""", [user_id]).fetchall()
            removed["projects"].extend(list(projects))
            projects_history = g_db.execute("""SELECT id, uid, user_id, status, data, storage, start_time, end_time 
                                                 FROM projects_history
                                                WHERE user_id = %s""", [user_id]).fetchall()
            projects_uids = list(set([p["uid"] for p in projects_history]))
            removed["projects_history"].extend(list(projects_history))
            if len(projects_uids) > 0:
                project_files = g_db.execute("""SELECT id, project_uid, filename, key, size, data, storage, create_date, 
                                                       change_date, delete_date 
                                                     FROM project_files
                                                    WHERE project_uid IN ("""+
                                                        ", ".join(["%s"]*len(projects_uids)) + ")",
                                             projects_uids).fetchall()
                removed["project_files"].extend(list(project_files))

                account_entries = g_db.execute("""SELECT id, user_id, amount, description, date, job_id, computing_start, 
                                                         computing_end, price_snapshot
                                                    FROM user_accounts
                                                   WHERE user_id = %s""", [user_id]).fetchall()
                removed["user_accounts"].extend(list(account_entries))

                jobs = g_db.execute("""SELECT id, user_id, project_uid, status, progress, operation_id, 
                                              provider_cost_id, machine_price_id, nbr_machines, create_date, start_time,
                                              end_time, logs, debug                     
                                         FROM jobs
                                        WHERE user_id = %s""", [user_id]).fetchall()
                removed["jobs"].extend(list(jobs))

                meshes = g_db.execute("""SELECT id, project_uid, name, result_file_id, preview_file_id, status, job_id,
                                                create_date, delete_date
                                           FROM meshes
                                          WHERE project_uid IN ("""+ ", ".join(["%s"]*len(projects_uids)) + ")",
                                      projects_uids).fetchall()
                removed["meshes"].extend(list(meshes))

                calcs = g_db.execute("""SELECT id, project_uid, name, mesh_id, params_file_id, status_file_id, 
                                               result_file_id, internal_file_id, status, job_id, last_start_date, 
                                               last_stop_date, create_date, delete_date, iterations_file_id, 
                                               reduce_file_id
                                          FROM calculations
                                         WHERE project_uid IN ("""+ ", ".join(["%s"]*len(projects_uids)) + ")",
                                     projects_uids).fetchall()
                removed["calculations"].extend(list(calcs))

                # Deleted stored entries
                g_db.execute("DELETE FROM calculations WHERE project_uid IN ("+", ".join(["%s"]*len(projects_uids))+")",
                             projects_uids)
                g_db.execute("DELETE FROM meshes WHERE project_uid IN (" + ", ".join(["%s"] * len(projects_uids)) + ")",
                             projects_uids)
                g_db.execute("DELETE FROM jobs WHERE user_id = %s", [user_id])
                g_db.execute("DELETE FROM user_accounts WHERE user_id = %s", [user_id])
                g_db.execute("DELETE FROM project_files WHERE project_uid IN ("+", ".join(["%s"]*len(projects_uids)) + ")",
                             projects_uids)
            g_db.execute("DELETE FROM projects_history WHERE user_id = %s", [user_id])
            g_db.execute("DELETE FROM projects WHERE user_id = %s", [user_id])
            g_db.execute("DELETE FROM users WHERE id = %s", [user_id])

    for old_login, new_login in action_data["TO_RENAME"].items():
        g_db.execute(u"UPDATE users SET login = %s WHERE login = %s", [new_login, old_login])

    for login, email in action_data["EMAIL_LIST"].items():
        g_db.execute("UPDATE users SET email = %s WHERE login = %s", [email, login])

    # We check everything is fine
    no_email_users = g_db.execute("SELECT * FROM users WHERE email IS NULL").fetchall()
    if len(no_email_users) > 0:
        utf8_login_list = [u['login'].encode('ascii', 'xmlcharrefreplace') for u in no_email_users]
        err_msg = "There is still users without emails: "+", ".join(utf8_login_list)
        raise RuntimeError(err_msg)
    all_logins = [u["login"] for u in g_db.execute("SELECT login FROM users").fetchall()]
    for login in all_logins:
        if clean_login(login) != login:
            raise RuntimeError("Invalid login: '"+clean_login(login)+"' != '"+login.encode('ascii', 'xmlcharrefreplace')+"'")
    all_emails = [u["email"].encode('ascii', 'xmlcharrefreplace') for u in g_db.execute("SELECT email FROM users").fetchall()]
    for email in all_emails:
        if not is_email_valid(email):
            raise RuntimeError("Invalid email: '" + email + "'")

    with open(bkp_data_file, 'w') as f:
        pickle.dump(removed, f)


def downgrade():
    import core.api_util
    import lib.pg_util

    conn = op.get_bind()

    try:
        domain = context.get_context().config.get_main_option("domain")
    except StandardError as e:
        sys.stderr.write(os.linesep + "Warning: " + str(e) + os.linesep)
        sys.stderr.flush()
        domain = None

    if domain is None or domain not in SERVER_DATA.keys():
        domain = "default"
    g_db = core.api_util.DatabaseContext.get_conn()
    action_data = SERVER_DATA[domain]
    for old_login, new_login in action_data["TO_RENAME"].items():
        g_db.execute("UPDATE users SET login = %s WHERE login = %s", [old_login, new_login])

    # Restore deleted users
    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)

        for line in data['users']:
            g_db.execute("""INSERT INTO users (id, login, pwd, salt, user_rank, create_date, delete_date) 
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6]])

        for line in data['projects']:
            g_db.execute("""INSERT INTO projects (id, uid, user_id, status, data, storage)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5]])
        for line in data['projects_history']:
            g_db.execute("""INSERT INTO projects_history (id, uid, user_id, status, data, storage, start_time, 
                                                          end_time)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7]])
        for line in data['project_files']:
            g_db.execute("""INSERT INTO project_files (id, project_uid, filename, key, size, data, storage, 
                                                       create_date, change_date, delete_date)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8], line[9]])
        for line in data['user_accounts']:
            g_db.execute("""INSERT INTO user_accounts (id, user_id, amount, description, date, job_id, 
                                                       computing_start, computing_end, price_snapshot)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8]])
        for line in data['jobs']:
            g_db.execute("""INSERT INTO jobs (id, user_id, project_uid, status, progress, operation_id, 
                                              provider_cost_id, machine_price_id, nbr_machines, create_date, 
                                              start_time, end_time, logs, debug)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8], line[9],
                          line[10], line[11], line[12], line[13]])
        for line in data['meshes']:
            g_db.execute("""INSERT INTO meshes (id, project_uid, name, result_file_id, preview_file_id, status,
                                                job_id, create_date, delete_date)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8]])
        for line in data['calculations']:
            g_db.execute("""INSERT INTO calculations (id, project_uid, name, mesh_id, params_file_id, 
                                                      status_file_id, result_file_id, internal_file_id, status, 
                                                      job_id, last_start_date, last_stop_date, create_date, 
                                                      delete_date, iterations_file_id, reduce_file_id)
                            OVERRIDING SYSTEM VALUE 
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                         [line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8], line[9],
                          line[10], line[11], line[12], line[13], line[14], line[15]])
