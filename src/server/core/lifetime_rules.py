# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import datetime

# Project specific libs
from lib import util
from lib import date_util
from lib import error_util


class Penalty(object):
    """ Enum type defining what to do about an instance"""
    DEATH = 1  # Kill
    PROBATION = 2  # Email Warning


class Motive(object):
    """ Enum type to define the cause of the action against an instance"""
    NOT_JOINABLE = 1  # The instance is not joinable
    NO_JOBID = 2  # The instance is not related to an actual job
    NOT_WORKING = 3  # The instance do nothing
    TOO_LONG = 4  # The instance is running for too long
    STUCK_STOPPING = 5  # The instance is stuck for too long
    NO_MASTER = 6  # A cluster slave has no relative cluster master worker


class LifetimeRules(object):
    def __init__(self, conf_path):
        """
        This object contains all the allowed duration threshold.
        :param conf_path:   Path to the config file
        :type conf_path:    String
        """
        self._rules = {}
        config = util.load_ini_file(conf_path)
        self._rules = {
            Penalty.DEATH:  {
                Motive.NOT_JOINABLE: LifetimeRules._read_conf(config, 'not_joinable_kill'),
                Motive.NO_JOBID: LifetimeRules._read_conf(config, 'no_jobid_kill'),
                Motive.NOT_WORKING: LifetimeRules._read_conf(config, 'not_working_kill'),
                Motive.TOO_LONG: LifetimeRules._read_conf(config, 'too_long_kill')
            },
            Penalty.PROBATION: {
                Motive.NOT_JOINABLE: LifetimeRules._read_conf(config, 'not_joinable_warning'),
                Motive.NO_JOBID: LifetimeRules._read_conf(config, 'no_jobid_warning'),
                Motive.NOT_WORKING: LifetimeRules._read_conf(config, 'not_working_warning'),
                Motive.TOO_LONG: LifetimeRules._read_conf(config, 'too_long_warning'),
                Motive.STUCK_STOPPING: LifetimeRules._read_conf(config, 'stuck_stopping_warning')
            }
        }

    def get_rules(self, penalty):
        """
        Get all the duration threshold configured for warning and killing

        :param penalty:     The penalty you want to get the thresholds
        :type penalty:      int
        :return:            The list of motive threshold
        :rtype:             dict[Optional[datetime.timedelta]]
        """
        return self._rules[penalty]

    def get_threshold(self, penalty, motive):
        """
        Get the duration threshold configured for a specific motive

        :param penalty:     The penalty you want to get the thresholds
        :type penalty:      int
        :param motive:      The motive
        :type motive:       int
        :return:            The duration threshold
        :rtype:             datetime.timedelta|None
        """
        return self._rules[penalty][motive]

    @staticmethod
    def _read_conf(config, key):
        """
        Read the configuration file to get the threshold of a specific check

        :param config:      The loaded and parsed configuration file
        :type config:       ConfigParser.ConfigParser
        :param key:         The config key to load
        :type key:          str
        :return:            The data inside the config file, or None
        :rtype:             datetime.timedelta
        """
        try:
            value = config.getint('garbage_collection', key)
        except error_util.abort_errors: raise
        except error_util.all_errors:
            return None
        if value <= 0:
            return None
        return datetime.timedelta(seconds=value)


class Sentence(object):
    """ Represent an action we will should apply to an instance """

    def __init__(self, penalty, motive, instance_value):
        """
        Contruct the sentence

        :param penalty:         The type of action to do (see Penalty values)
        :type penalty:          int
        :param motive:          The reason why we should do apply this penalty (see Motive values)
        :type motive:           int
        :param instance_value:  The problematic value found on a specific instance
        :type instance_value:   datetime.datetime|None
        """
        super(Sentence, self).__init__()
        self._penalty = penalty                # The type of action to do (see Penalty values), type: int
        self._motive = motive                  # Why we should do apply this penalty (see Motive values), type: int
        self._instance_value = instance_value  # The problematic value found, type: datetime.datetime

    @property
    def penalty(self):
        """  The type of action to do (see Penalty values), :rtype int """
        return self._penalty

    @property
    def motive(self):
        """  The reason why we should do apply this penalty (see Motive values), :rtype int """
        return self._motive

    @property
    def description(self):
        """ Get a full description of the sentence, :rtype str """
        if self._motive == Motive.NOT_JOINABLE:
            result = "The instance is not joinable (ssh) for too long\n"
            if self._instance_value is None:
                result += "No connection has succeed on this instance\n"
            else:
                result += "last connection happened "+Sentence._format_date(self._instance_value)+"\n"
        elif self._motive == Motive.NO_JOBID:
            return "The instance is not related to a job"
        elif self._motive == Motive.NOT_WORKING:
            result = "The instance is not doing any job\n"
            if self._instance_value is None:
                result += "The instance was never observed working\n"
            else:
                result += "last job finished "+Sentence._format_date(self._instance_value)+"\n"
        elif self._motive == Motive.TOO_LONG:
            result = "The instance is running for too long\n"
            result += "The instance started "+Sentence._format_date(self._instance_value)+"\n"
        elif self._motive == Motive.STUCK_STOPPING:
            result = "The instance is stopping for a long time\n"
            if self._instance_value is None:
                result += "The instance was never observed working\n"
            else:
                result += "The instance stop working "+Sentence._format_date(self._instance_value)+"\n"
        else:
            raise RuntimeError("Unknown motive: "+str(self._motive))
        # FIXME SAM: reimplement this
        # result += "The threshold is defined to fire after "
        # result += utils.duration_to_hr(Sentence._get_rules(self._penalty)[self._motive])
        return result

    def __eq__(self, other):
        return self._motive == other.motive and self._penalty == other.penalty

    @staticmethod
    def _format_date(moment, round_time=True):
        """
        Returns a humanized string representing a date and time

        :param moment:      The date and time you want to display
        :type moment:       datetime.datetime
        :param round_time:  Do you want an approximate duration string (default True)
        :type round_time:   Optional[bool]
        :return:            A humanized string representing time difference
        :rtype:             str
        """
        now = datetime.datetime.utcnow()
        duration = now - moment
        if round_time:
            duration = date_util.round_duration(duration)
        return date_util.duration_to_hr(duration)+" ago ("+moment.strftime("%c")+")"
